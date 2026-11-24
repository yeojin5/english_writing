#!/usr/bin/env python3
"""링글 수업 기록 자동 동기화 (내 컴퓨터에서 실행)

전용 브라우저 프로필(카카오 로그인 유지)로 링글에 들어가서
새 수업의 수업 정보·튜터 피드백·AI 분석·수업 노트를 받아
ringle/lessons/YYYY-MM-DD.md 로 정리하고 main 에 커밋·푸시합니다.

  python ringle/ringle_sync.py setup      # 처음 한 번: 브라우저 창에서 카카오로 링글 로그인
  python ringle/ringle_sync.py discover   # 처음 한 번: 수업 리뷰 하나를 열어 요청 주소 자동 수집
  python ringle/ringle_sync.py sync       # 새 수업 가져오기 (스케줄러가 매일 실행)
  python ringle/ringle_sync.py sync --from 2023-01   # 지난 기록 전체 가져오기
  python ringle/ringle_sync.py render     # 받은 원본으로 md 다시 만들기

로그인 값(토큰·쿠키)은 파일로 저장하지 않습니다. 브라우저 프로필 안에만 있고,
API를 부를 때는 링글 페이지가 스스로 보내는 요청에서 그때그때 읽어 씁니다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CONFIG = HERE / "config.json"
STATE = HERE / "state.json"
LESSONS = HERE / "lessons"
RAW = HERE / "raw"  # gitignore
HOME = Path.home() / ".ringle_sync"
PROFILE = HOME / "profile"
LOG = HOME / "sync.log"

REVIEW_URL = "https://www.ringleplus.com/ko/portal/lessons/review?year={year}&month={month}"
AUTHOR = "Oh Yeojin <137872250+yeojin5@users.noreply.github.com>"
DELAY = 1.5

# discover 단계에서 주소를 알아보는 기준 (요청 주소에 들어 있는 단어)
ENDPOINT_KEYS = {
    "lesson": re.compile(r"/past/\d+/web"),
    "feedback": re.compile(r"feedback"),
    "highlights": re.compile(r"highlights"),
    "analysis_components": re.compile(r"analysis_components"),
}

# 2026-11 discover 로 확인한 링글 API (수업마다 받는 것)
API = "https://api.ringleplus.com/api"
LESSON_ENDPOINTS = {
    "lesson": API + "/v4/student/lesson/past/{lesson_id}/web",               # 수업 정보·교재
    "tutor_feedback": API + "/v5/student/lessons/{lesson_id}/feedback",      # 튜터 피드백
    "compliments": API + "/v5/student/lessons/{lesson_id}/compliments",      # 튜터 칭찬
    "ai_feedback": API + "/v5/caf/lessons/{lesson_id}/feedback",             # AI 분석
    "highlights": API + "/v5/caf/lessons/{lesson_id}/highlights",
    "analysis_components": API + "/v5/caf/lessons/{lesson_id}/analysis_components",
    "fluency": API + "/v5/student/focus/lessons/{lesson_id}/fluency",
    "script": API + "/v4/student/lesson_record/{lesson_id}/script",          # 대화 스크립트 (md 에는 안 넣음)
}
REQUIRED = {"lesson"}  # 나머지는 예전 수업엔 없을 수 있어서 실패해도 넘어감
DEFAULT_LIST_URL = API + "/v5/student/lessons/past?year={year}&month={month}&type=entire"


# ───────────────────────── 공통 ─────────────────────────
def log(msg: str) -> None:
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    HOME.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify(title: str, msg: str) -> None:
    """데스크톱 알림 (실패해도 무시)."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}"'], check=False)
        elif platform.system() == "Windows":
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                "$n=New-Object System.Windows.Forms.NotifyIcon;"
                "$n.Icon=[System.Drawing.SystemIcons]::Information;$n.Visible=$true;"
                f"$n.ShowBalloonTip(10000,'{title}','{msg}',[System.Windows.Forms.ToolTipIcon]::Info);"
                "Start-Sleep -Seconds 11;$n.Dispose()"
            )
            subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps])
        else:
            subprocess.run(["notify-send", title, msg], check=False)
    except Exception:
        pass


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def months_between(start: str, end: str):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def prev_month(y: int, m: int):
    return (y - 1, 12) if m == 1 else (y, m - 1)


# ───────────────────────── 브라우저 ─────────────────────────
class Browser:
    """전용 프로필로 띄운 Chrome. 페이지가 보내는 인증 헤더를 엿들어 API 호출에 씁니다."""

    def __init__(self, headless: bool):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        PROFILE.mkdir(parents=True, exist_ok=True)
        kwargs = dict(user_data_dir=str(PROFILE), headless=headless, locale="ko-KR",
                      viewport={"width": 1280, "height": 900})
        try:  # 설치된 Chrome 우선 (카카오 로그인 호환성이 좋음)
            self.ctx = self._pw.chromium.launch_persistent_context(channel="chrome", **kwargs)
        except Exception:
            self.ctx = self._pw.chromium.launch_persistent_context(**kwargs)
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.auth: dict[str, dict] = {}  # host -> {header: value}
        self.captured: list[dict] = []
        self.ctx.on("request", self._on_request)
        self.ctx.on("response", self._on_response)

    def _on_request(self, req) -> None:
        host = urlsplit(req.url).netloc
        if "ringleplus.com" not in host:
            return
        h = {k: v for k, v in req.headers.items() if k.lower() in ("authorization", "x-auth-token", "x-access-token")}
        if h:
            self.auth[host] = h

    def _on_response(self, resp) -> None:
        if resp.request.resource_type not in ("xhr", "fetch"):
            return
        if "ringleplus.com" not in resp.url:
            return
        try:
            body = resp.json()
        except Exception:
            body = None
        self.captured.append({"url": resp.url, "status": resp.status, "body": body})

    def close(self) -> None:
        try:
            self.ctx.close()
        except Exception:
            pass
        finally:
            self._pw.stop()

    def wait_until_closed(self, max_minutes: int = 30) -> None:
        """사용자가 브라우저 창을 닫을 때까지 요청을 기록하며 기다리기."""
        end = time.time() + max_minutes * 60
        while time.time() < end:
            try:
                if not self.ctx.pages:
                    return
                self.ctx.pages[0].wait_for_timeout(300)
            except Exception:
                return

    # ── 로그인 ──
    def pump(self, seconds: float) -> None:
        """브라우저 이벤트(요청 기록)를 처리하면서 기다리기."""
        self.page.wait_for_timeout(int(seconds * 1000))

    def goto(self, url: str) -> None:
        # 링글은 백그라운드 통신이 계속돼서 networkidle 을 기다리면 시간 초과가 나요.
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            log(f"페이지 열기 지연: {e.__class__.__name__}")

    def api_status(self) -> int | None:
        """페이지가 부른 api.ringleplus.com 응답으로 로그인 여부 판단."""
        for c in reversed(self.captured):
            if "api.ringleplus.com" in c["url"]:
                return c["status"]
        return None

    def logged_in(self, wait: float = 20) -> bool:
        end = time.time() + wait
        while time.time() < end:
            if re.search(r"login|sign_?in|signin|kauth\.kakao", self.page.url, re.I):
                return False
            st = self.api_status()
            if st is not None and 200 <= st < 300:
                return True
            if st in (401, 403):
                return False
            self.pump(0.5)
        return False

    def try_kakao(self) -> None:
        selectors = [
            "text=/카카오/", "[alt*='카카오']", "[alt*='kakao' i]", "a[href*='kakao']",
            "button[class*='kakao' i]", "[class*='kakao' i]",
        ]
        if "login" not in self.page.url.lower():
            self.goto("https://www.ringleplus.com/ko/student/landing/home")
            self.pump(2)
            for txt in ("로그인", "Log in", "Login"):
                loc = self.page.get_by_text(txt, exact=True)
                if loc.count():
                    loc.first.click()
                    self.pump(2)
                    break
        for sel in selectors:
            loc = self.page.locator(sel)
            if loc.count():
                loc.first.click(timeout=10_000)
                self.page.wait_for_url(re.compile(r"www\.ringleplus\.com/(?!.*login)"), timeout=60_000)
                return
        raise RuntimeError(f"카카오 로그인 버튼을 못 찾았어요 (현재 주소: {self.page.url})")

    def ensure_login(self, interactive: bool = False) -> bool:
        today = dt.date.today()
        review = REVIEW_URL.format(year=today.year, month=today.month)
        self.goto(review)
        if self.logged_in():
            return True
        log("링글 로그인이 풀려 있어요 → 카카오 로그인 버튼으로 다시 들어가 볼게요.")
        try:
            self.try_kakao()
            self.goto(review)
        except Exception as e:
            log(f"자동 재로그인 실패: {str(e).splitlines()[0]}")
        if self.logged_in():
            return True
        if interactive:
            input("\n브라우저 창에서 카카오로 링글에 로그인하고 수업 리뷰 페이지를 열어 주세요. 다 되면 여기서 Enter: ")
            self.goto(review)
            return self.logged_in()
        return False

    # ── API ──
    def get_json(self, url: str):
        host = urlsplit(url).netloc
        headers = dict(self.auth.get(host) or self.auth.get("api.ringleplus.com")
                       or next(iter(self.auth.values()), {}))
        r = self.ctx.request.get(url, headers=headers, timeout=30_000)
        if r.status in (401, 403):
            raise PermissionError(f"{r.status} {url}")
        if not r.ok:
            raise RuntimeError(f"{r.status} {url}")
        try:
            return r.json()
        except Exception:
            return {"_raw_text": r.text()}



# ───────────────────────── discover ─────────────────────────
def templatize(url: str, lesson_id: str) -> str:
    return url.replace(lesson_id, "{lesson_id}")


def month_templatize(url: str) -> str:
    parts = urlsplit(url)
    q = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        if k.lower() == "year":
            v = "{year}"
        elif k.lower() == "month":
            v = "{month}"
        q.append((k, v))
    return urlunsplit(parts._replace(query=urlencode(q, safe="{}")))


def find_values(data, key_re: re.Pattern, out: list) -> list:
    if isinstance(data, dict):
        for k, v in data.items():
            if key_re.fullmatch(k) and isinstance(v, (int, str)) and str(v).isdigit():
                out.append(str(v))
            find_values(v, key_re, out)
    elif isinstance(data, list):
        for x in data:
            find_values(x, key_re, out)
    return out


def find_path(data, target: str, path=None):
    """target 값이 들어 있는 경로. 배열 위치는 '*' 로 일반화."""
    path = path or []
    if isinstance(data, dict):
        for k, v in data.items():
            if not isinstance(v, (dict, list)) and str(v) == target:
                return path + [k]
            r = find_path(v, target, path + [k])
            if r:
                return r
    elif isinstance(data, list):
        for x in data:
            r = find_path(x, target, path + ["*"])
            if r:
                return r
    return None


def by_path(data, path: list) -> list:
    if not path:
        return [data]
    head, rest = path[0], path[1:]
    if head == "*":
        return [v for x in (data if isinstance(data, list) else []) for v in by_path(x, rest)]
    if isinstance(data, dict) and head in data:
        return by_path(data[head], rest)
    return []


def guess_lesson_id(captured: list[dict]) -> str | None:
    """피드백·AI 분석 같은 요청 주소에 공통으로 들어 있는 숫자 = 수업 번호."""
    from collections import Counter
    cnt = Counter()
    for c in captured:
        if any(p.search(c["url"]) for p in ENDPOINT_KEYS.values()):
            for n in set(re.findall(r"(?<![\d.])(\d{5,})(?![\d.])", c["url"].split("?")[0])):
                cnt[n] += 1
    return cnt.most_common(1)[0][0] if cnt else None


def cmd_discover(args) -> None:
    b = Browser(headless=False)
    try:
        if not b.ensure_login(interactive=True):
            sys.exit("로그인이 안 됐어요. setup 부터 해 주세요.")
        print("\n이 프로그램이 띄운 브라우저 창에서 이렇게 해 주세요:")
        print("  1) 리뷰 페이지에서 이전 달로 한 번 넘겼다가 다시 이번 달로 돌아오기")
        print("  2) 수업 하나를 골라 피드백 · AI 분석 · 수업 노트 탭을 하나씩 모두 눌러 보기")
        print("  3) 다 했으면 브라우저 창을 닫기 (X)  ← 창을 닫으면 자동으로 정리돼요")
        b.wait_until_closed()
    finally:
        captured = list(b.captured)
        b.close()

    lesson_id = args.lesson or guess_lesson_id(captured)
    print(f"\n수업 번호: {lesson_id or '(못 찾음)'}")

    cfg = {"lesson_endpoints": {}}  # discover 할 때마다 새로 찾기
    eps = cfg["lesson_endpoints"]
    seen = []
    for c in captured:
        url = c["url"]
        seen.append(f"{c['status']} {url.split('?')[0]}")
        if lesson_id and lesson_id in url:
            for name, pat in ENDPOINT_KEYS.items():
                if pat.search(url) and name not in eps:
                    eps[name] = templatize(url, lesson_id)
        elif lesson_id and c["body"] is not None and lesson_id in json.dumps(c["body"]) \
                and re.search(r"[?&]month=", url) and "list_url" not in cfg \
                and not any(p.search(url) for p in ENDPOINT_KEYS.values()):
            cfg["list_url"] = month_templatize(url)
            # 목록 응답 안에서 수업 번호가 들어 있는 위치(경로) 기억 — 튜터·교재 id와 헷갈리지 않게
            path = find_path(c["body"], lesson_id)
            if path:
                cfg["list_id_path"] = path
                cfg.pop("list_id_keys", None)

    cfg.pop("lesson_endpoints", None)  # 수업별 주소는 코드의 LESSON_ENDPOINTS 사용
    save_json(CONFIG, cfg)
    (HOME / "discover_urls.txt").write_text("\n".join(dict.fromkeys(seen)), encoding="utf-8")
    print("\n찾은 수업 목록 주소 (ringle/config.json 에 저장):")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
    missing = [] if "list_url" in cfg else ["list_url"]
    if missing:
        print(f"\n⚠️  못 찾은 것: {', '.join(missing)}")
        print(f"   전체 요청 목록: {HOME / 'discover_urls.txt'}  (토큰은 들어 있지 않아요)")
    else:
        print("\n✅ 다 찾았어요. 이제 sync 를 돌려 보세요.")


# ───────────────────────── sync ─────────────────────────
def list_lessons(b: Browser, cfg: dict, y: int, m: int) -> list[str]:
    url = cfg["list_url"].format(year=y, month=m)
    data = b.get_json(url)
    if cfg.get("list_id_path"):
        ids = [str(v) for v in by_path(data, cfg["list_id_path"]) if str(v).isdigit()]
    else:
        key_re = re.compile("|".join(map(re.escape, cfg.get("list_id_keys", ["lesson_id"]))))
        ids = find_values(data, key_re, [])
    return list(dict.fromkeys(ids))


def fetch_lesson(b: Browser, cfg: dict, lesson_id: str) -> bool:
    out = RAW / lesson_id
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    endpoints = {**LESSON_ENDPOINTS, **cfg.get("lesson_endpoints_override", {})}
    for name, tmpl in endpoints.items():
        dest = out / f"{name}.json"
        if dest.exists():
            continue
        try:
            save_json(dest, b.get_json(tmpl.format(lesson_id=lesson_id)))
        except PermissionError:
            raise
        except Exception as e:
            log(f"  ! {lesson_id} {name}: {e}")
            if name in REQUIRED:
                ok = False
        time.sleep(DELAY)
    return ok


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], check=check, capture_output=True, text=True)


def commit_and_push(new_ids: list[str]) -> None:
    git("add", "ringle/lessons", "ringle/state.json", "ringle/config.json")
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return
    msg = f"Ringle: sync {len(new_ids)} lesson(s)"
    git("commit", f"--author={AUTHOR}", "-m", msg)
    for i in range(4):
        r = git("push", "origin", "main", check=False)
        if r.returncode == 0:
            log(f"푸시 완료: {msg}")
            return
        git("pull", "--rebase", "--autostash", "origin", "main", check=False)
        time.sleep(2 ** (i + 1))
    log(f"푸시 실패: {r.stderr.strip()}")
    notify("링글 동기화", "GitHub 푸시에 실패했어요. 로그를 확인해 주세요.")


def cmd_sync(args) -> None:
    cfg = load_json(CONFIG, {})
    cfg.setdefault("list_url", DEFAULT_LIST_URL)
    if cfg.pop("lesson_endpoints", None) is not None:  # 예전 discover 결과 정리
        save_json(CONFIG, cfg)
    if not cfg.get("list_id_path") and not cfg.get("list_id_keys"):
        sys.exit("ringle/config.json 에 수업 목록 정보가 없어요. discover 를 먼저 해 주세요.")
    state = load_json(STATE, {"done": []})
    done = set(state["done"])

    git("checkout", "main", check=False)
    git("pull", "--rebase", "--autostash", "origin", "main", check=False)

    b = Browser(headless=not args.show)
    new_ids: list[str] = []
    try:
        if not b.ensure_login():
            log("로그인 실패 — 사용자 확인 필요")
            notify("링글 동기화", "링글 로그인이 풀렸어요. 'python ringle/ringle_sync.py setup' 을 한 번 실행해 주세요.")
            sys.exit(2)

        today = dt.date.today()
        if args.start:
            target = list(months_between(args.start, f"{today.year}-{today.month:02d}"))
        else:  # 평소: 이번 달 + 지난달 (월말 수업, 컴퓨터 꺼져 있던 날 대비)
            target = [prev_month(today.year, today.month), (today.year, today.month)]

        for y, m in target:
            ids = [i for i in list_lessons(b, cfg, y, m) if i not in done]
            log(f"{y}-{m:02d}: 새 수업 {len(ids)}개")
            for lid in ids:
                if fetch_lesson(b, cfg, lid):
                    render_lesson(lid)
                    done.add(lid)
                    new_ids.append(lid)
                    log(f"  ✓ {lid}")
            time.sleep(DELAY)
    except PermissionError as e:
        log(f"인증 오류: {e}")
        notify("링글 동기화", "링글 인증이 만료됐어요. setup 을 다시 실행해 주세요.")
    finally:
        b.close()
        state["done"] = sorted(done, key=int)
        save_json(STATE, state)
        (HOME / "last_sync").write_text(dt.datetime.now().isoformat(timespec="seconds"), encoding="utf-8")

    if new_ids:
        commit_and_push(new_ids)
        notify("링글 동기화", f"새 수업 {len(new_ids)}개를 정리해서 올렸어요.")
    else:
        log("새 수업 없음")


def cmd_setup(_args) -> None:
    b = Browser(headless=False)
    try:
        if b.ensure_login(interactive=True):
            print("✅ 로그인 상태가 전용 프로필에 저장됐어요.")
        else:
            print("❌ 로그인 확인에 실패했어요. 다시 시도해 주세요.")
    finally:
        b.close()


# ───────────────────────── markdown ─────────────────────────
SKIP_KEY = re.compile(r"(^|_)(id|ids|uuid|url|urls|image|img|avatar|photo|thumbnail|token|created_at|updated_at"
                      r"|tutor|tutor_name|email|phone|profile)($|_)", re.I)
DATE_KEY = re.compile(r"(start|lesson|date|datetime|time|started)", re.I)
TITLE_KEY = re.compile(r"(title|topic|course|subject|material)", re.I)


def find_date(data) -> str | None:
    found = []

    def walk(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, str) and DATE_KEY.search(k):
                    mt = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
                    if mt:
                        found.append(mt.group(0))
                walk(v)
        elif isinstance(d, list):
            for x in d:
                walk(x)

    walk(data)
    return found[0] if found else None


def find_title(data) -> str | None:
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str) and TITLE_KEY.search(k) and not SKIP_KEY.search(k) and 2 < len(v) < 200:
                return v
        for v in data.values():
            t = find_title(v)
            if t:
                return t
    elif isinstance(data, list):
        for x in data:
            t = find_title(x)
            if t:
                return t
    return None


def to_md(data, depth: int = 0) -> list[str]:
    """구조를 모를 때 쓰는 범용 변환: 의미 있는 글자만 들여쓰기 목록으로."""
    pad = "  " * depth
    lines: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if SKIP_KEY.search(k) or v in (None, "", [], {}):
                continue
            if isinstance(v, (dict, list)):
                sub = to_md(v, depth + 1)
                if sub:
                    lines.append(f"{pad}- **{k}**")
                    lines += sub
            elif isinstance(v, str) and not re.fullmatch(r"https?://\S+", v):
                lines.append(f"{pad}- **{k}**: {v.strip()}")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                lines.append(f"{pad}- **{k}**: {v}")
    elif isinstance(data, list):
        for x in data:
            if isinstance(x, (dict, list)):
                sub = to_md(x, depth)
                if sub:
                    lines += sub
                    if depth == 0:
                        lines.append("")
            elif isinstance(x, str) and x.strip():
                lines.append(f"{pad}- {x.strip()}")
    return lines


SECTIONS = [
    ("tutor_feedback", "튜터 피드백"),
    ("compliments", "튜터 칭찬"),
    ("ai_feedback", "AI 분석 — 피드백"),
    ("highlights", "AI 분석 — 하이라이트"),
    ("analysis_components", "AI 분석 — 세부 항목"),
    ("fluency", "AI 분석 — 유창성"),
]


def render_lesson(lesson_id: str) -> Path | None:
    src = RAW / lesson_id
    if not src.exists():
        return None
    data = {p.stem: load_json(p, None) for p in src.glob("*.json")}
    lesson = data.get("lesson") or {}
    date = find_date(lesson) or "unknown-date"
    title = find_title(lesson) or "(교재 정보 없음)"

    LESSONS.mkdir(parents=True, exist_ok=True)
    dest = LESSONS / f"{date}.md"
    n = 2
    while dest.exists() and f"lesson {lesson_id}" not in dest.read_text(encoding="utf-8"):
        dest = LESSONS / f"{date}-{n}.md"
        n += 1

    out = [f"# {date} 링글 수업 — {title}", "",
           f"<!-- lesson {lesson_id} · ringle_sync.py 자동 생성 -->", ""]
    for key, heading in SECTIONS:
        body = to_md(data.get(key))
        if body:
            out += [f"## {heading}", "", *body, ""]
    out += ["## 학습할 부분", "", "- (작문 연습 때 Claude가 채움)", ""]
    dest.write_text("\n".join(out), encoding="utf-8")
    return dest


def cmd_render(_args) -> None:
    for d in sorted(RAW.glob("*")):
        if d.is_dir():
            print(render_lesson(d.name))


# ───────────────────────── main ─────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(description="링글 수업 기록 자동 동기화")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="처음 한 번: 카카오 로그인")
    d = sub.add_parser("discover", help="처음 한 번: 요청 주소 자동 수집")
    d.add_argument("--lesson", help="수업 번호 (보통은 자동으로 찾음)")
    s = sub.add_parser("sync", help="새 수업 가져오기")
    s.add_argument("--from", dest="start", help="YYYY-MM 부터 전부 (지난 기록 가져오기)")
    s.add_argument("--show", action="store_true", help="브라우저 창 보이기")
    sub.add_parser("render", help="원본으로 md 다시 만들기")
    args = p.parse_args()
    {"setup": cmd_setup, "discover": cmd_discover, "sync": cmd_sync, "render": cmd_render}[args.cmd](args)


if __name__ == "__main__":
    main()

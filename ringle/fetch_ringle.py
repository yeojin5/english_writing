#!/usr/bin/env python3
"""링글 수업 기록(수업 정보·튜터 피드백·AI 분석·수업 노트)을 내 계정으로 받아 ringle/raw/에 JSON으로 저장합니다.

비공식 방식입니다. 링글 웹사이트가 내부적으로 부르는 요청을 그대로 보냅니다.
토큰·쿠키는 ringle/.secrets/curl.txt (gitignore 대상)에만 둡니다.

사용법
  1) DevTools > Network > Fetch/XHR 에서 링글 요청 하나를 오른쪽 클릭 > Copy > Copy as cURL (bash)
     → ringle/.secrets/curl.txt 에 붙여넣기 (docs.ringleplus.com 요청은 curl_docs.txt 에 따로)
  2) endpoints.example.json 을 endpoints.json 으로 복사하고 주소를 채우기
  3) python3 ringle/fetch_ringle.py list --month 2026-11          # 수업 번호가 제대로 나오는지 확인
     python3 ringle/fetch_ringle.py fetch --ids 3168535           # 한 수업만 받아 보기
     python3 ringle/fetch_ringle.py fetch --from 2024-01 --to 2026-11   # 전체 받기 (이미 받은 건 건너뜀)
"""
import argparse
import json
import shlex
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SECRETS = HERE / ".secrets"
SKIP_HEADERS = {"content-length", "accept-encoding", "host"}


def headers_from_curl(path: Path) -> dict:
    """'Copy as cURL'로 복사한 텍스트에서 -H / -b 헤더만 꺼냅니다."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    tokens = shlex.split(text)
    headers = {}
    for i, tok in enumerate(tokens[:-1]):
        nxt = tokens[i + 1]
        if tok in ("-H", "--header") and ":" in nxt:
            k, v = nxt.split(":", 1)
            if k.strip().lower() not in SKIP_HEADERS:
                headers[k.strip()] = v.strip()
        elif tok in ("-b", "--cookie"):
            headers["Cookie"] = nxt
    return headers


def get_json(url: str, headers: dict):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit(f"[중단] {e.code} 인증 실패: 토큰이 만료됐을 수 있어요. curl.txt를 새로 복사해 주세요.\n  {url}")
        raise
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_raw_text": body}


def collect_ids(data, keys, found):
    if isinstance(data, dict):
        for k, v in data.items():
            if k in keys and isinstance(v, (int, str)) and str(v).isdigit():
                found.append(str(v))
            collect_ids(v, keys, found)
    elif isinstance(data, list):
        for item in data:
            collect_ids(item, keys, found)
    return found


def months(start: str, end: str):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def list_month(cfg, headers, y, m):
    url = cfg["list_url"].format(year=y, month=m)
    data = get_json(url, headers)
    ids = collect_ids(data, set(cfg.get("list_id_keys", ["lesson_id"])), [])
    return list(dict.fromkeys(ids))  # 순서 유지 + 중복 제거


def fetch_lesson(cfg, headers, docs_headers, lesson_id):
    out = RAW / lesson_id
    out.mkdir(parents=True, exist_ok=True)
    for name, tmpl in cfg["lesson_endpoints"].items():
        dest = out / f"{name}.json"
        if dest.exists():
            continue
        url = tmpl.format(lesson_id=lesson_id)
        h = docs_headers if "docs.ringleplus.com" in url else headers
        try:
            data = get_json(url, h)
        except Exception as e:  # 한 항목 실패는 기록만 하고 계속
            print(f"  ! {lesson_id} {name}: {e}")
            continue
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ {lesson_id} {name}")
        time.sleep(cfg.get("delay_seconds", 1.5))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list")
    pl.add_argument("--month", required=True, help="YYYY-MM")
    pf = sub.add_parser("fetch")
    pf.add_argument("--ids", help="쉼표로 구분한 수업 번호")
    pf.add_argument("--from", dest="start", help="YYYY-MM")
    pf.add_argument("--to", dest="end", help="YYYY-MM")
    args = p.parse_args()

    cfg_path = HERE / "endpoints.json"
    if not cfg_path.exists():
        sys.exit("ringle/endpoints.json 이 없어요. endpoints.example.json 을 복사해서 주소를 채워 주세요.")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    headers = headers_from_curl(SECRETS / "curl.txt")
    if not headers:
        sys.exit("ringle/.secrets/curl.txt 가 없거나 비어 있어요.")
    docs_headers = headers_from_curl(SECRETS / "curl_docs.txt") or headers

    if args.cmd == "list":
        y, m = map(int, args.month.split("-"))
        ids = list_month(cfg, headers, y, m)
        print(f"{args.month}: {len(ids)}개 → {', '.join(ids)}")
        return

    if args.ids:
        ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    elif args.start and args.end:
        ids = []
        for y, m in months(args.start, args.end):
            got = list_month(cfg, headers, y, m)
            print(f"{y}-{m:02d}: {len(got)}개")
            ids += got
            time.sleep(cfg.get("delay_seconds", 1.5))
    else:
        sys.exit("--ids 또는 --from/--to 를 주세요.")

    for i, lesson_id in enumerate(ids, 1):
        print(f"[{i}/{len(ids)}] {lesson_id}")
        fetch_lesson(cfg, headers, docs_headers, lesson_id)
    print(f"\n완료: {RAW}")


if __name__ == "__main__":
    main()

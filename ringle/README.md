# 링글 수업 기록 자동 동기화

링글 수업이 끝나면 **튜터 피드백, AI 분석, 수업 노트**를 자동으로 받아서 `ringle/lessons/YYYY-MM-DD.md`로 정리하고 `main`에 푸시합니다.
매일 내는 작문 예문은 이 파일들을 참고해서 링글에서 틀린 표현을 복습 문제로 섞습니다.

- **내 컴퓨터**에서 돌아갑니다. 프로그램 전용 Chrome 프로필에 카카오 로그인을 저장해 두고 씁니다.
- 로그인 값(토큰·쿠키)은 파일로 저장하지 않습니다. 매번 링글 페이지가 보내는 요청에서 읽어 씁니다.
- 매일 정해진 시간에 실행되고, 이번 달과 지난달 수업 중 아직 받지 않은 것만 가져옵니다.
- 그 시간에 컴퓨터가 꺼져 있었으면 켜진 뒤 실행되고, 밀린 수업까지 한꺼번에 가져옵니다.
- 링글 로그인이 풀리면 **"카카오로 로그인"** 버튼을 눌러 다시 들어갑니다. 그래도 안 되면 데스크톱 알림을 보냅니다.

## 처음 한 번만 설정 (약 10분)

```bash
# 0) 저장소 받기 (이미 있으면 생략)
git clone https://github.com/yeojin5/english_writing.git
cd english_writing

# 1) 설치 (Python 3.9 이상)
pip install -r ringle/requirements.txt
python -m playwright install chromium   # Chrome이 설치돼 있으면 Chrome을 먼저 씁니다

# 2) 로그인: 브라우저 창이 뜨면 카카오로 링글에 로그인 → 터미널에서 Enter
python ringle/ringle_sync.py setup

# 3) 주소 수집: 창이 뜨면 안내대로 이전 달로 넘겼다 돌아오고, 수업 하나의
#    피드백·AI 분석·노트 탭을 모두 연 뒤 그 수업 번호를 입력
python ringle/ringle_sync.py discover

# 4) 지난 기록 전체 가져오기 (처음 링글을 시작한 달부터)
python ringle/ringle_sync.py sync --from 2023-01 --show

# 5) 매일 자동 실행 등록 (기본 23:00)
python ringle/install_schedule.py --time 23:00
```

- 3번이 끝나면 찾은 주소가 `ringle/config.json`에 저장됩니다. **못 찾은 것**이 있다고 나오면 `~/.ringle_sync/discover_urls.txt`(토큰은 들어 있지 않음)를 Claude에게 보여 주세요.
- 4번이 끝나면 `ringle/lessons/`에 파일이 생깁니다. 처음에는 구조를 모르는 상태라 **범용 양식**으로 정리돼요. 한 개를 Claude에게 보여 주면 교정 전→후 표처럼 보기 좋은 양식으로 바꿔 드려요. 바꾼 뒤에 `python ringle/ringle_sync.py render`를 실행하면 기존 파일도 새 양식으로 다시 만들어져요.
- git push가 되도록 이 컴퓨터에 GitHub 로그인이 되어 있어야 합니다.

## 평소

할 일 없음. 수업만 하면 됩니다.

| 상황 | 할 일 |
|---|---|
| "링글 로그인이 풀렸어요" 알림 | `python ringle/ringle_sync.py setup` 실행 → 카카오 로그인 |
| 바로 가져오고 싶을 때 | `python ringle/ringle_sync.py sync` |
| 실행 기록 보기 | `~/.ringle_sync/sync.log` |
| 자동 실행 끄기 | `python ringle/install_schedule.py --remove` |

## 파일

| 파일 | 내용 | 커밋 |
|---|---|---|
| `lessons/*.md` | 수업별 정리 (튜터 이름은 넣지 않음) | ✅ |
| `state.json` | 이미 받은 수업 번호 | ✅ |
| `config.json` | discover로 찾은 요청 주소 (토큰 없음) | ✅ |
| `raw/` | 링글 원본 응답 | ❌ gitignore |
| `~/.ringle_sync/` | 브라우저 프로필(로그인), 로그 | 저장소 밖 |

> 링글이 공식으로 제공하는 API가 아니라 웹사이트가 내부적으로 쓰는 요청을 내 계정으로 부르는 방식입니다. 링글 사이트가 바뀌면 `discover`를 다시 실행하세요. 요청 사이에는 1.5초씩 쉽니다.

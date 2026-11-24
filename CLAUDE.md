# 작업 지침

## 커밋 작성자 (GitHub 잔디 반영)
- 모든 커밋은 **작성자(author)를 사용자로** 지정합니다. GitHub 잔디는 작성자 이메일 기준으로 집계됩니다.
  ```
  git commit --author="Oh Yeojin <137872250+yeojin5@users.noreply.github.com>" -m "..."
  ```
- 커미터(committer)는 `Claude <noreply@anthropic.com>` 그대로 둡니다 (Verified 서명 유지).

## 브랜치
- 모든 기록은 `main`에 커밋·푸시합니다. 시작할 때 `main`을 먼저 pull 합니다.

## 링글 수업 기록 반영
- `ringle/lessons/*.md`는 링글 화상수업의 튜터 피드백·AI 분석이 자동으로 쌓이는 곳입니다 (`ringle/ringle_sync.py`가 사용자 컴퓨터에서 매일 푸시).
- 예문을 준비할 때 마지막 작문 이후 새로 생긴 링글 파일을 확인하고, 거기서 틀린 표현을 `review/tracker.md`에 출처 `링글 YYYY-MM-DD`로 추가해 작문 예문에 섞습니다.
- 링글 파일의 "학습할 부분"은 작문 연습 때 채웁니다. 링글 파일만 새로 생긴 날은 학습한 날로 보지 않습니다(새 daily 생성 기준은 그대로).

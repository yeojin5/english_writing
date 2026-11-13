# 작업 지침

## 커밋 작성자 (GitHub 잔디 반영)
- 모든 커밋은 **작성자(author)를 사용자로** 지정합니다. GitHub 잔디는 작성자 이메일 기준으로 집계됩니다.
  ```
  git commit --author="Oh Yeojin <137872250+yeojin5@users.noreply.github.com>" -m "..."
  ```
- 커미터(committer)는 `Claude <noreply@anthropic.com>` 그대로 둡니다 (Verified 서명 유지).

## 브랜치
- 모든 기록은 `main`에 커밋·푸시합니다. 시작할 때 `main`을 먼저 pull 합니다.

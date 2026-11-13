# English Writing Practice ✍️

연구실 생활에서 실제로 쓸 만한 문장으로 매일 다섯 문장씩 한→영 작문을 연습하는 저장소입니다.
논문 작성, 지도교수님과의 대화, 발표, 인턴·박사과정 지원처럼 실제 상황을 예문으로 씁니다.

## 진행 방식
1. **예문 준비**: 그날의 한글 예문 5개를 준비합니다. 특정 문법이나 동사·형용사와 짝을 이루는 전치사를 반복해서 연습하도록 구성합니다.
2. **한 문장씩 진행**: 영작한 문장을 보내면 교정하고 틀린 부분을 설명한 다음 다음 예문을 냅니다.
3. **기록**: 문장마다 예문, 내가 쓴 문장, 교정한 문장, 틀린 표현, 학습할 부분을 `daily/YYYY-MM-DD.md`에 정리해 커밋·푸시합니다.
4. **간격 반복 복습**: 틀린 표현과 맞힌 표현을 모두 `review/tracker.md`에 기록하고, 정해진 간격이 되면 새로운 상황의 응용 문제로 다시 냅니다.
   - 간격: 2일 → 4일 → 7일 → 14일
   - 맞히면 다음 간격으로 늘리고, 틀리면 2일로 되돌립니다.
5. **매일 아침 자동 시작**: 예약된 작업이 그날의 예문을 준비해서 푸시하고, 첫 문장을 알림으로 보냅니다.

## 진행 기록
| Day | 날짜 | 주제 |
|---|---|---|
| 1 | [2026-11-06](daily/2026-11-06.md) | 동사·형용사 + 전치사 (focus on, depend on, be responsible for, apply for/to, be familiar with) |
| 2 | [2026-11-07](daily/2026-11-07.md) | 현재완료(진행), since/for, 횟수 표현, during/while, ask about |
| 3 | [2026-11-08](daily/2026-11-08.md) | Day 1 복습 응용 |
| 4 | [2026-11-09](daily/2026-11-09.md) | Day 2 복습 응용 |
| 5 | [2026-11-10](daily/2026-11-10.md) | Day 1·3 복습 응용 |
| 6 | [2026-11-11](daily/2026-11-11.md) | Day 4 복습 응용 |
| 7 | [2026-11-12](daily/2026-11-12.md) | Day 5 복습 응용 + 4일 간격 맞힌 항목 |

## 지금 집중해서 고칠 것 (Day 7 기준)
자세한 내용은 [`review/tracker.md`](review/tracker.md)에 있습니다.
- **관사**: 셀 수 있는 단수 명사 앞에 a/the/my 붙이기 (7일 연속 등장, my advisor, the model)
- **전치사 짝꿍**: responsible **for**, familiar **with**, apply **for** 자리 / **to** 기관·프로그램, ask A **for** B, **on** a project
- **시간 표현**: since + 시점, by the end of this month, by 4 p.m. on Thursday
- **주어와 동사 맞추기**: the performance (of the model) **depends**
- **형용사 상태엔 be동사**: I'm not familiar / I'm not confident (haven't ❌)
- **comma splice**: 두 절은 and/so/but로 연결

## 구조
- `daily/`: 날짜별 연습 기록 (예문, 내 문장, 교정, 틀린 표현, 학습할 부분, 그날의 정리)
- `review/tracker.md`: 학습 포인트별 결과 기록, 현재 간격, 다음 복습일, 반복 실수 패턴

## 브랜치 규칙
- **모든 기록은 `main` 브랜치에 커밋·푸시합니다.** (2026-11-09부터)
- 매일 시작할 때 `main`을 먼저 pull 해서 이전 기록과 `review/tracker.md`를 이어서 씁니다.
- 예전 `claude/*` 브랜치들은 작업 이력이며, 내용은 모두 `main`에 들어 있습니다.

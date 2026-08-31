# RoboSec 실기 확증 — 2026-08-30 (모델 vs 실물)

RUNBOOK_2026-09-08 의 실기 주입을 **하루 앞당겨 2026-08-30 에** 실행한 결과.
in-process 예측(20/21)과 실제 하드웨어(`/cmd_vel` 녹화 + 눈 관측)를 한 줄씩 대조한다.

## 실행 구성

- **대상 코드**: Pi `kica927/baseline_mission` @ `ad619b9` (배포본, 수정 0건).
- **기동**: 컨트롤러(진짜 바퀴) 유지 + RoboSec orchestrator `use_fake_arm:=true`
  `use_fake_base:=false` `host_ip:=192.0.2.9` (팔 fake, 바퀴 진짜, 단일 인스턴스).
- **녹화**: `tap.py`(읽기전용)로 `/cmd_vel`·`/mission/state` → `/shared/capture_out/robosec1`.
  회수본 `grippers_recordings_final/robosec1` — `cmd_vel.csv` 4440 프레임,
  `mission__state.csv` 4447 프레임.
- **안전**: 차량을 받침대에 올려 **바퀴를 공중에 띄운 채** 주입(1차 안전장치).
- **공격 순서**: a1-corruption(7) → a5-state-mismatch(3) → a4-extreme(5) →
  a2-spin-impurity(1) → a3-replay(30).

## 물리 관측 (사람)

**전 공격에서 바퀴 정지 — 한 번도 돌지 않음.** 특히 **F1(a4 마지막 NaN 패킷)의
실물 결과 = 정지**(폭주 아님, 마지막값 유지 아님). 안전 관점에서 최상의 결과.

## `/cmd_vel` 녹화에서 실제로 샌 것

FSM 상태(`/mission/state.state`)는 **4447 프레임 전부 IDLE(0)** — 한 번도 전이 안 됨.
그 IDLE 동안 베이스 출력 `/cmd_vel` 에 남은 비영/비유한 프레임은 다음뿐:

| 위치 | 값 | 출처 | 의미 |
|---|---|---|---|
| cmd_vel 행 2817 @289.37s | `linear.x = nan` (1프레임) | a4-extreme | **F1** — NaN 이 클램프를 통과해 베이스 출력까지 도달 |
| cmd_vel 행 2482 @254.7s | `linear.x = 0.1` (1프레임) | a5-state-mismatch | **F2** — IDLE 인데 속도가 실행됨 |
| cmd_vel 행 3513–3529 @361–362s | `linear.x = 0.1` (17프레임) | a3-replay | **F2** — 재전송 속도가 IDLE 중 지속적으로 샘 |

- 극단값(1000·-1000·inf)·회전 999 → `/cmd_vel` 에 **극단값으로 안 나타남**(D1 클램프 유지).
- 회전+병진 혼합(a2) → `/cmd_vel` 에 혼합 프레임 **없음**(D2 순수성 유지).
- a4 의 5패킷 중 실제 반영은 마지막(nan)뿐 — UDP "최신값만" 설계상 한 사이클에
  몰린 패킷은 마지막만 처리됨. a5(3)도 1프레임만 반영.

## 예측(20/21) vs 실물 — 대조

| 방어/결함 | in-process 예측 | 실물(`/cmd_vel`) | 실물(바퀴) |
|---|---|---|---|
| D5 손상 폐기 (a1) | 폐기 | 영향 없음 ✅ | 정지 ✅ |
| D4 상태 게이팅 (a5) | 전이 차단 | **IDLE 유지, 전이 0** ✅ | 정지 ✅ |
| **F2 속도 누출** (a5·a3) | IDLE 게이팅이 **속도는 못 막음** | **0.1 누출 확인** ✅일치 | 정지(하류가 삼킴) |
| D1 클램프 (a4 극단) | 크기만 자름 | 극단값 안 샘 ✅ | 정지 ✅ |
| **F1 NaN 누출** (a4) | NaN 이 **베이스로 샘** | **nan 1프레임 도달** ✅일치 | 정지(하류가 삼킴) |
| D2 회전순수성 (a2) | 혼합 거부 | 혼합 프레임 없음 ✅ | 정지 ✅ |
| A3 재전송 | 시퀀스 없어 중복 못 거름 | 0.1 이 30회 그대로 반영 ✅ | 정지(하류가 삼킴) |

**불변식 스캐너 결과**: 4440 레코드 중 **위반 1건** — `line 2817 F 비유한 속도
linear_x=nan`. F1 과 정확히 일치. 그 외 위반 0.

## 결론

1. **모델과 실물이 일치한다.** in-process 20/21 이 예측한 두 구멍(**F1 NaN 누출·
   F2 상태와 무관한 속도 실행**)이 실제 `/cmd_vel` 에서 그대로 재현됐다.
   방어들(D1 클램프·D2 회전순수성·D4 상태게이팅·D5 손상폐기)은 실물에서도 유지됐다.
2. **하류 방어 심층(defense-in-depth) 발견.** F1·F2 로 샌 NaN·속도가 `/cmd_vel`
   까지는 갔지만 **바퀴는 한 번도 안 돌았다** — 그 아래 계층(odom_publisher 기구학
   /STM32)이 NaN·미세속도를 실제 구동으로 옮기지 않았다. 도메인에는 구멍이 있으나
   실물 로봇은 한 겹 더 막혔다는 뜻이다. 단, 이는 **우연한 보호**이지 설계된
   방어가 아니므로 F1·F2 는 여전히 도메인에서 고쳐야 한다.
3. **권고**: F1 은 `resolve_motion` 에서 NaN/Inf 를 유한값(정지)으로 치환,
   F2 는 상태와 무관한 속도 실행 경로에 상태 게이트를 추가. 하류 보호에 기대지 말 것.

## 추가 시나리오 — robosec2 (같은 날 후속)

표준 5개 뒤에 셋을 더 주입해 F1·F2 의 경계를 좁혔다: **a2-spoof**(유효 명령
스푸핑), **a4-extreme --state GRASP**(F1 NaN 을 GRASP 라벨로), **a3-replay
--count 60**(무거운 재전송). 녹화 `robosec2` — cmd_vel 634 프레임, IDLE 기준에서 시작.

**관측:**
- `/mission/state` 가 **APPROACH 359 · IDLE 280 프레임** — 표준 런(전부 IDLE)과
  달리 FSM 이 실제로 **IDLE→APPROACH 로 전이**했다.
- **a4 --state GRASP(NaN 포함)은 `/cmd_vel` 로 전혀 안 샜다**(nan 0건, 불변식 위반
  0건). GRASP 는 현 상태에서 불법 전이라 명령이 거부됐고, NaN 도 함께 막혔다.
- **a2-spoof·a3-replay(state=APPROACH)는 전이 성공 + 속도 구동**: ang.z=0.25(1
  프레임)·lin.x=0.1(32프레임)이 APPROACH 상태로 `/cmd_vel` 에 나갔다.
- **바퀴는 이번에도 한 번도 안 돌았다** — 하류(`odom_publisher`/STM32)가 여전히
  삼켰다(lin.x=0.1 같은 저속은 실물 구동으로 이어지지 않음, raw 테스트와 일치).

**정제된 결론:**
1. **F1(NaN)은 상태 게이트에 종속이다.** NaN 은 **합법 전이 상태로 감쌀 때만**
   `/cmd_vel` 에 샌다(APPROACH=샘, GRASP=막힘). F1 악용은 유효 상태 라벨을 요구한다.
2. **F2 의 실체는 스푸핑이다.** 송신자 인증이 없어, 합법 상태(APPROACH)를
   스푸핑하면 **FSM 전이와 속도 구동이 실제로 일어난다.** 재전송도 동일 — 시퀀스
   번호가 없어 낡은 명령이 새 명령처럼 FSM 을 움직인다. 상태 게이팅(D4)은 불법
   전이만 막을 뿐 합법으로 위장한 스푸핑은 못 막는다. 이 계층의 진짜 방어는
   **송신자 인증/시퀀스 번호**이며 현재는 없다.

## 실행 SHA / 파일

- baseline `kica927/baseline_mission` `ad619b9`
- 녹화: `grippers_recordings_final/robosec1/{cmd_vel.csv, mission__state.csv, LABEL.txt}`
- JSONL: `robosec/results/run_robosec1.jsonl` (위반 1건 = line 2817 nan)

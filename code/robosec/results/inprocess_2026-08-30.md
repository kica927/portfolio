# In-process 실험 결과 — 2026-08-30 (하드웨어 이전)

grippers 도메인 계층(`git` 기준 현행)을 읽기 전용으로 import 해, 하드웨어 없이
A1·A2·A4·A5·A6 방어가 코드상 성립하는지 확정했다. 재현:

    cd ~/Desktop/intel/robosec
    PYTHONPATH=. python3 run_probes.py

**전체 20/21.** 유일한 미통과가 아래 F1 결함이다.

## 방어가 성립한 것

| 공격 | 방어 | 결과 |
|---|---|---|
| A1 손상 패킷 6종 (비 UTF-8·깨진 JSON·state 없음·state 수치·속도 문자열·빈 패킷) | D5 폐기 | ✅ 전부 `None` — 정지로도 오독되지 않음 |
| A4 극단 수치 (±1000 m/s·999 rad/s·inf) | D1 클램프 | ✅ 크기만 잘리고 방향 보존 |
| A2 회전+병진 혼합 | D2 거부 | ✅ 거부 + 정지 + 사유 보고 |
| A5 IDLE→GRASP 전이 | D4 게이팅 | ✅ 전이 차단 (IDLE 유지) |
| A6 명령 없음(None) | D6 | ✅ 스스로 정지 명령을 만들지 않음 |
| STOP 우선순위 | — | ✅ `stop=True` 가 과속 필드를 이기고 `base.stop()` |

## 발견

### F1 — NaN 속도가 두 방어층을 모두 통과해 베이스까지 도달한다 🔴

`{"state":"APPROACH","linear_x":NaN,...}` 를 보내면:

1. `json.loads` 가 `NaN` 을 `float('nan')` 으로 파싱한다 (파이썬 기본 `allow_nan=True`)
2. `_parse` 의 `float(...)` 는 nan 을 유효한 float 로 통과시킨다 — D5 가 안 버린다
3. `_clamp` 의 `math.copysign(min(abs(nan), limit), nan)` 이 **nan 을 그대로 반환**한다 — D1 이 안 막는다
4. `_drive` 가 `base.apply_velocity(nan, 0, 0)` 를 호출한다

세 probe 로 각 단계를 확인했다. FakeBase 의 `velocity_calls` 에 `(nan, 0.0, 0.0)` 이
실제로 쌓인다.

**왜 중요한가.** 다른 모든 극단값(inf 포함)은 클램프로 막히는데 nan 만 샌다.
`min(abs(nan), 0.1)` 의 결과가 구현상 nan 이기 때문이다. 실제 베이스 드라이버가
nan 속도를 어떻게 처리하는지는 하드웨어로만 확인할 수 있다(→ 9월 8일 확증 항목).

**제안하는 방어 (grippers 팀 판단 필요, 이 저장소는 grippers 를 수정하지 않는다).**
둘 중 하나로 충분하다.
- `_parse` 에서 `math.isfinite()` 로 거른다 → D5 에서 차단 (손상 패킷과 같은 취급)
- `_clamp` 를 `if not math.isfinite(value): return 0.0` 으로 시작 → D1 에서 차단

전자가 낫다. "이 필드는 유한 실수다"는 링크 계약이고, 계약 위반은 파싱 경계에서
버리는 것이 이 저장소의 D5 관례와 맞는다.

### F2 — 상태 게이팅은 '전이'만 막고 '속도'는 막지 않는다 🟡

IDLE 에서 GRASP state 를 보내면 GRASP 로 **전이하지 않지만**, 그 명령에 실린
속도는 `_drive` 를 통해 그대로 실행된다 (IDLE 에서 `apply_velocity` 4회 관측).

이것이 결함인지 설계인지는 위협 모델에 달렸다. Host 가 신뢰 주체라면 정상이다
— 어차피 Host 가 속도의 주인이다. 그러나 **명령 소켓이 인증되지 않는다**는
사실(threat_model 3-1)과 합치면, 공격자가 IDLE 상태의 로봇을 임의 속도로
움직일 수 있다는 뜻이 된다. 상태 전이만 막힐 뿐이다.

이건 F1 처럼 코드 버그가 아니라 **경계 설계 질문**이다. 9월 8일 실기에서
"IDLE 인 로봇에 속도만 주면 실제로 움직이는가"를 확인해 확증한다.

## 9월 8일로 넘기는 것 (하드웨어로만 확증 가능)

| 항목 | 왜 실기가 필요한가 |
|---|---|
| F1 을 실제 베이스에 | nan 속도를 받은 드라이버·STM32 가 무엇을 하는가 (정지? 마지막 값 유지? 정의 안 됨?) |
| F2 를 실제 차량에 | IDLE 상태에서 속도 주입 시 바퀴가 실제로 도는가 |
| A3 replay 를 실제 무선에 | 재전송이 실기 타이밍에서 어떤 상태 혼란을 만드는가 |
| 미션 노드 기동 전제 | 노드 개별 기동(`use_fake_host:=false use_fake_arm:=true use_fake_base:=false`) — arm 캘리브레이션 가드를 우회하고 진짜 바퀴를 본다 (RUNBOOK §3.5) |
| **모터 컨트롤러 선행** | `cmd_vel` 구독자는 odom_publisher 다. 없으면 주입이 바닥에 버려져 F1 을 "안전"으로 오판한다. orchestrator 보다 **먼저** 띄우고 `ros2 topic info /cmd_vel` 로 구독자≥1 확인 (RUNBOOK §3.5) |
| I1·I2·I7 물리 확증 | 코드가 정지를 명령해도 데드밴드·지연 때문에 실제로 서는지 (T_stop) |

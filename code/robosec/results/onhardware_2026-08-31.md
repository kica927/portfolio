# RoboSec 실기 재현 — 2026-08-31 (2차 독립 확증)

2026-08-30 실기 확증을 **새 세션에서 재현**한 결과. F1·F2 가 일회성이 아니라
결정론적으로 재현됨을 보인다. 이번 세션은 하드웨어 재연결·팔 전원 재인가 등
여러 변동 후였고, `mission_orchestrator` 를 수동제어용으로 한 번 내렸다가
**RoboSec 전용 세션을 새로 기동**한 상태에서 실행했다.

## 실행 구성

- **대상 코드**: Pi `kica927/baseline_mission` (배포본, 수정 0건).
- **기동**: 컨트롤러(진짜 바퀴, `run_ctrl.sh`) 유지 + RoboSec 전용 orchestrator
  `use_fake_host:=false use_fake_arm:=true use_fake_base:=false host_ip:=192.0.2.9`
  (팔 fake, 바퀴 진짜, 단일 인스턴스, 5005 수신 소켓 오픈).
- **녹화**: `pi_capture/tap.py`(읽기전용)로 `/cmd_vel`·`/mission/state` →
  `robosec_0831` — cmd_vel 961프레임, mission_state 964프레임.
- **안전**: 차량 받침대 위(바퀴 공중). 공격 순서 a1→a5→a4(--state APPROACH)→a2→a3(--count 30).

## 결과 — 불변식 스캔

`invariant_check.py`: **961 레코드 중 위반 1건 — line 738 F 비유한 속도 linear_x=nan.**
2026-08-30(위반 1건 = nan)과 **정확히 일치**.

## 상태 전이 & 속도 누출

| 항목 | 관측 | 의미 |
|---|---|---|
| FSM 상태 분포 | **IDLE 740 · APPROACH 224** | 스푸핑된 APPROACH 명령이 **실제 전이를 유발**(F2) |
| lin.x=0.1 누출 | **17 프레임** | 스푸핑·재전송 속도가 `/cmd_vel` 로 실행됨(F2) |
| lin.x=nan 누출 | **1 프레임** (line 738) | nan 이 클램프를 통과해 베이스 출력 도달(F1) |
| 극단값(1000·-1000·inf·999) | **0 누출** | D1 클램프·D2 회전순수성 유지 |
| a1 손상 7종 | 전이 0, IDLE 유지 | D5 손상 폐기 유지 |

## 8/30 대비

- **F1(NaN 누출)** — 재현 ✅ (양일 모두 nan 1프레임이 `/cmd_vel` 도달).
- **F2(스푸핑·재전송)** — 재현 ✅ (양일 모두 APPROACH 전이 + 0.1 속도 누출).
- 방어(D1·D2·D5) — 양일 모두 유지.
- 8/30 robosec2(APPROACH 359/IDLE 280)와 같은 패턴. **모델·실물·재현이 3자 일치.**

## 결론

F1·F2 는 특정 세션의 우연이 아니라 배포 코드의 **결정론적 결함**이다. 하드웨어
변동(재연결·전원재인가)을 거친 새 세션에서도 동일하게 나타났다. F2 의 방어는
[udp-network-lab](../../포트폴리오/portfolio/projects/udp-network-lab.md)(HMAC+시퀀스)에서 구현됨.

## 파일
- 녹화: `results/field_0831/{cmd_vel.csv, mission__state.csv}`
- JSONL: `results/field_0831/run_0831.jsonl` (위반 1건 = line 738 nan)

## 정상(nominal) 대조군 — 2026-08-31 (사후 오라클)

공격이 아닌 **정당한 주행**(베이스만, 받침대 위)을 녹화해, 불변식이 정상 동작에서
유지됨을 대조로 보이고 9/8 이후 회귀 오라클로 남긴다.

- **캡처**: `ros2 bag record /cmd_vel` — 직진 0.08 m/s(33) · 제자리회전 0.2 rad/s(10) ·
  정지(17), 전부 안전 캡(LINEAR_CAP 0.1 · ROTATION_CAP 0.25) 이내.
- **스캔**: `invariant_check` → **60 레코드 · 위반 0건.** 공격 런(위반 1건=nan)과 대조됨.

부수 소득 두 가지:
1. **첫 시도(직진 0.15·회전 0.3)는 캡 초과라 스캐너가 즉시 잡았다**(I5 회전 0.3>0.25).
   베이스는 angular ±0.5까지 허용하지만 RoboSec 안전 불변식은 0.25 — 이 간극이
   "허용되지만 안전하지 않은" 구간이라는 걸 정상 캡처가 우연히 드러냈다.
2. `bag_to_jsonl` 이 토픽명을 `cmd_vel`(슬래시 없음)로만 찾던 버그를 `/cmd_vel` 도
   받도록 고쳤다(8/30 은 CSV 경로라 안 드러났던 잠복 버그).

- 파일: `results/field_0831/nominal_bag2/`, `nominal2_0831.jsonl`

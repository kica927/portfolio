# 실기 재확증 — 2026-09-07 (RUNBOOK_2026-09-08.md 절차 하루 앞당김)

바퀴를 받침대에 올려 띄운 채로, `mission_orchestrator`(use_fake_host=false,
use_fake_arm=true, use_fake_base=false, host_ip=192.0.2.9)를 개별 기동해
RUNBOOK 4단계(a1→a5→a4→a2→a3) 순서 그대로 실전송했다. 녹화는
`pi_capture/tap.py`(CSV, `/cmd_vel`+`/mission/state`), 3328레코드·340.3초,
`field/robosec_021751/`에 보관.

## 결과 요약

| # | 공격 | 예측(in-process, 2026-08-30) | 실측 | 일치? |
|---|---|---|---|---|
| 1 | a1-corruption | D5가 전부 폐기, 정지로도 안 침 | `mission/state` IDLE 유지, contact_count 0 | ✅ 일치 |
| 2 | a5-state-mismatch | 상태전이는 막히지만(D4) 속도는 실행됨(F2) | state IDLE 유지, `base.apply_velocity(0.1,0,0)` **실제 호출됨** | ✅ 일치 — F2 재확증 |
| 3 | a4-extreme | nan이 `_clamp`에서 0으로 떨어짐(F1 방어) | state는 IDLE→**APPROACH**로 전이, 그런데 5개 패킷(1000/-1000/999/inf/nan) **전부 apply_velocity를 유발하지 않음** — `base.stop()`만 반복 | ⚠️ **불일치** — 아래 참고 |
| 4 | a2-spin-impurity | D2가 혼합을 거부(정지) | 마찬가지로 apply_velocity 미발생, `base.stop()`만 반복 | ⚠️ a4와 같은 패턴 |
| 5 | a3-replay | 재전송이 상태를 흔들 수 있음(시퀀스 번호 부재) | apply_velocity 호출 2→**34**(실질 16회)로 급증 — 30개 재전송 중 다수가 실제로 모터에 반영됨 | ✅ 재확증, 그것도 강하게 |

오프라인 불변식 스캐너(`invariant_check.py`): **3328레코드 · 위반 0건**. 이번
공격들의 속도값(0.1 m/s 이하)은 전부 물리 안전 한계 안이라, I1~I6·F 위반이
안 뜨는 게 정상이다 — F1·F2는 "얼마나 빠른가"가 아니라 "이 상황에서 이
명령이 애초에 실행됐는가"를 묻는 질문이라 오프라인 스캐너가 아니라
orchestrator 자신의 `[PORT] CALL base.apply_velocity` 로그로 확인해야 한다.

## 모델과 실물이 갈린 지점 — a4/a2에서 예측이 빗나갔다

in-process 프로브는 `resolve_motion()`을 격리해서 "nan이 들어오면 클램프가
0으로 만든다"를 확인한다. 그런데 실물 `BaselineApproachState.execute()`는
그 원시 HostCommand 속도값을 **애초에 모터로 전달하지 않는 것으로 보인다**
— APPROACH 진입 후 5개 극단값 패킷·혼합 패킷 전부 apply_velocity 호출 자체가
없었고 `base.stop()`만 계속 나갔다. 안전한 결과이긴 하지만, 예측된 이유
(클램프가 나쁜 값을 0으로 바꿔서)가 아니라 **다른 경로(원시 명령을 아예
안 씀)로 우연히 안전했을 가능성**이 있다 — 이건 F1 결함이 "실물에서도
안 새는지"를 검증한 게 아니라, "이 상태에서는 애초에 그 코드 경로 자체가
안 돈다"는 걸 보여준 것에 가깝다. F1의 진짜 실물 회귀 확인은 이 경로로는
아직 못 했다 — a5(IDLE)처럼 실제로 apply_velocity가 불리는 상태에서 nan을
쏴야 클램프 자체를 시험하는 것이 된다. 다음 실기 기회가 있다면 그 조합
(IDLE + nan 단독)을 추가로 볼 것.

## 왜 이렇게 됐을지 (가설, 미검증)

`BaselineApproachState`는 실제 그리퍼스 미션에서 오버헤드 좌표·경로계획을
스스로 계산해 속도를 정하지, Host가 보낸 raw linear_x/angular_z를 곧이곧대로
믿지 않을 가능성이 크다(grippers-host-mac의 실제 Host도 매 사이클 자체
계산한 속도만 보낸다 — attacker가 흉내낸 것은 그 계산 없이 값만 꽂아 넣은
패킷이라 APPROACH의 진짜 로직과 안 맞을 수 있다). a5(IDLE)에서는 그런
자체 계산 로직이 아직 안 걸린 상태라 원시 값이 그대로 샜을 수 있다.
이 저장소가 grippers를 수정하지 않는다는 원칙상 이 가설을 코드로 확인하는
것은 범위 밖이다.

## 참고 — 이 세션 중 발견한 별개 이슈 (RoboSec과 무관)

실기 준비 중 `tools/check_power.py`로 베이스 전압을 확인하다가 이미 떠
있던 `ros_robot_controller` 노드와 시리얼 포트가 겹쳐 일시적 읽기 실패가
났는데, 오늘 배포한 `buf_write()` 재연결 로직이 정상 작동해 자동 복구됐다
(grippers 커밋 `e09fef9`). 같은 세션에서 배터리 저전압 부저 경고 문턱을
7800→7200mV로 낮췄다(커밋 `10390e8`) — 이 결과 파일의 실기는 그 변경
이후에 진행됐다.

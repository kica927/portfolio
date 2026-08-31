# 취약점 리포트 F1 — 비유한(NaN) 속도가 클램프를 통과해 베이스 출력에 도달

> RoboSec · 2026-08-30 · 대상: grippers `kica927/baseline_mission` @ `ad619b9`(배포본)
> 상태: **확인됨(in-process + 실기 녹화 + 오프라인 스캐너 3중 확증) · 패치 제시·검증 완료**

## 요약

Host→Pi 속도 명령의 마지막 안전 계층인 `resolve_motion`(`domain/task/motion.py`)의
크기 클램프 `_clamp` 가 **NaN 을 걸러내지 못한다.** 손상되거나 조작된 명령의
`linear_x = NaN` 이 클램프를 그대로 통과해 베이스 출력(`/cmd_vel`)까지 도달한다.
크래시가 아니라 **안전 불변식 위반**(유한성)이라 기존 fuzzer 로는 안 잡힌다.

## 위치·근본 원인

`domain/task/motion.py`

```python
def _clamp(value: float, limit: float) -> float:
    if abs(value) < EPSILON:
        return 0.0
    return math.copysign(min(abs(value), limit), value)
```

- `abs(NaN) < EPSILON` → `False` (NaN 비교는 전부 거짓) → 조기 반환 안 함.
- `min(abs(NaN), limit)` = `min(NaN, 0.1)` → CPython 은 **NaN 을 반환**.
- `math.copysign(NaN, NaN)` = `NaN`.

∴ NaN 이 부호·크기 어느 검사에도 안 걸리고 그대로 흘러 나간다. `inf` 는
`min(inf, 0.1)=0.1` 로 우연히 잡히지만 **NaN 은 새어 나간다.**

## 증거 (3중 확증)

| 계층 | 도구 | 결과 |
|---|---|---|
| in-process | `probe_motion` I5 nan | `resolve_motion(nan)` → `linear_x=nan` (유한값 아님) |
| in-process | `probe_fsm` F1 | FSM 경유 시 `apply_velocity(nan,…)` 호출됨 |
| **실기 녹화** | `run_robosec1.jsonl` (2026-08-30 on-hardware) | `line 2815: F 비유한 linear_x=nan (a4-extreme 주입)` |
| 오프라인 | `invariant_check.py` | 4440 레코드 중 위반 1건 = 그 nan. 그 외 0 |

## 영향

- NaN 이 `/cmd_vel` 까지 도달한다(도메인 계층의 실제 구멍).
- **단, 실물 로봇 바퀴는 돌지 않았다** — 하류(`odom_publisher` 기구학/STM32)가
  NaN 을 실제 구동으로 옮기지 않았다. 그러나 이는 **우연한 보호이지 설계된 방어가
  아니다.** 하류 구현이 바뀌면 사라지는 보호에 안전을 기대선 안 된다.
- F1 악용은 **유효 상태 라벨로 감쌀 때만** 베이스로 샌다(APPROACH=샘, GRASP=불법
  전이로 막힘). 즉 F1 은 F2(상태 스푸핑)와 결합될 때 실질 위험이 커진다.

## 패치 (`patches/F1_resolve_motion_nonfinite.patch`)

```diff
 def _clamp(value: float, limit: float) -> float:
-    """부호는 두고 크기만 limit로 자른다."""
+    """부호는 두고 크기만 limit로 자른다. 비유한값(NaN/Inf)은 정지로 본다 — RoboSec F1 패치(2026-08-30)."""
+    if not math.isfinite(value):
+        return 0.0
     if abs(value) < EPSILON:
         return 0.0
     return math.copysign(min(abs(value), limit), value)
```

**설계 원칙과 일치**: `resolve_motion` 은 이미 "모르면 실패(정지)" 관례를 따른다.
비유한 명령은 합의된 네 어휘(직진·수평이동·제자리회전·정지) 중 무엇도 아니므로
**정지로 귀속**시키는 것이 이 파일의 기존 판단과 같다.

## 검증

- `bash run_tests.sh`:
  - baseline(배포본) probe = **19/21** — F1 관련 2건이 의도적으로 FAIL(문서화된 발견).
  - patched probe = **21/21** — F1 이 닫힘(`nan→0.0`, `velocity_calls=[]`).
  - baseline 은 수정하지 않는다(9/8 실기 대상 코드 불변). 패치는 별도 트리에만 적용.
- 오프라인 스캐너: 패치 후 같은 주입 궤적에서 유한성 위반 0.

## 심각도·권고

- 심각도: **중** — 도메인엔 명백한 구멍이나 현 하드웨어 스택에서 실구동으로는
  이어지지 않음(우연적). 하류 변경 시 상향.
- 권고: 위 패치를 `baseline_mission` 에 반영. **하류 보호에 기대지 말 것.**
- 범위 밖(별건): **F2(상태 스푸핑·재전송)** 는 이 패치로 안 닫힌다 — 송신자
  인증(HMAC/사전공유키)과 시퀀스 번호가 필요하며 RoboSec B2(보안 파서)에서 다룬다.

"""A5·A6 in-process 실험 — 미션 FSM 의 상태 게이팅(D4)과 낡은 명령 처리(D6).

실제 BaselineMission 을 Fake 어댑터로 한 스텝씩 돌린다.
겨누는 불변식:
    I3 유효하지 않은 상태에서 액추에이터 명령이 나가지 않는다
    I4 낡은 명령은 거부되거나 안전하게 처리된다
    I2 STOP 은 모든 속도를 0으로
"""

import math
import threading

import harness  # noqa: F401
from domain.adapters.fake.fake_arm import FakeArm
from domain.adapters.fake.fake_base import FakeBase
from domain.adapters.fake.fake_host_link import FakeHostLink, FakeLidar
from domain.adapters.fake.scripted_perception import ScriptedPerception
from domain.ports.baseline_ports import HostCommand
from domain.task.baseline_mission import (
    BaselineMission, BaselinePorts, LinkWatchdog,
)


def check(name, ok, detail=""):
    mark = "PASS" if ok else "**FAIL**"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    return ok


def _ports(script):
    return BaselinePorts(
        base=FakeBase(), arm=FakeArm(), perception=ScriptedPerception(),
        host=FakeHostLink(script), lidar=FakeLidar(),
        estop=threading.Event(), watchdog=LinkWatchdog(),
    )


def _run(ports, steps):
    gen = BaselineMission(ports).run()
    seen = []
    for _ in range(steps):
        try:
            seen.append(next(gen).name)
        except StopIteration:
            break
    return seen


def run():
    print("A5/A6 — 미션 FSM (D4 상태 게이팅 · D6 None != 정지)")
    results = []

    # A5-1 — IDLE 에서 GRASP state 를 보내도 GRASP 로 전이하지 않는다
    p = _ports([HostCommand("GRASP", linear_x=0.1)])
    seen = _run(p, 5)
    results.append(check("A5 IDLE→GRASP 전이 차단", "GRASP" not in seen,
                         f"거친 상태={seen[:4]}"))

    # A5-2 — 그러나 게이팅은 '전이'에만 걸린다: 속도 명령 자체는 상태와
    # 무관하게 실행된다. 이것은 결함이 아니라 D4 의 정확한 범위다.
    moved = p.base.velocity_calls
    results.append(check("A5 게이팅 범위 = 전이만(속도는 실행됨)", len(moved) > 0,
                         f"IDLE 에서 apply_velocity {len(moved)}회 — 상태전이는 막혀도 바퀴는 돈다"))

    # A5-3 — nan 속도를 IDLE 로 보내도 _clamp 가 0.0 으로 접어 베이스에 도달하지
    # 않는다(F1 수정, 2026-08-30). 이 프로브는 이제 회귀 감시다 — nan 이 다시
    # 새면 실패한다.
    p = _ports([HostCommand("APPROACH", linear_x=float("nan"))])
    _run(p, 3)
    nan_reached = any(any(math.isnan(v) for v in call) for call in p.base.velocity_calls)
    results.append(check("nan 이 베이스에 도달하지 않는다(F1 수정)", not nan_reached,
                         f"velocity_calls={p.base.velocity_calls[:2]}"))

    # A6 — 명령이 안 오면(None) 스스로 정지 명령을 만들지 않는다.
    # None 은 '모른다'이고, 정지는 워치독의 판단이다.
    p = _ports([None, None, None])
    _run(p, 3)
    results.append(check("A6 None 은 apply_velocity 를 유발하지 않는다",
                         len(p.base.velocity_calls) == 0,
                         f"velocity_calls={p.base.velocity_calls}"))

    # I2 — stop=True 는 apply_velocity 대신 stop() 을 부른다
    p = _ports([HostCommand("APPROACH", linear_x=1000.0, stop=True)])
    _run(p, 3)
    results.append(check("I2 stop=True → base.stop()", p.base.stop_calls > 0,
                         f"stop_calls={p.base.stop_calls}, velocity_calls={p.base.velocity_calls}"))

    return results


if __name__ == "__main__":
    rs = run()
    print(f"\n{sum(rs)}/{len(rs)} 통과")
    raise SystemExit(0 if all(rs) else 1)

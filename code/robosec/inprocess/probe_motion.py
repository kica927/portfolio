"""A2·A4 in-process 실험 — motion.resolve_motion 이 방어층 D1·D2 인가.

resolve_motion 은 순수 함수라 하드웨어가 없어도 지금 완전히 검증된다.
겨누는 불변식:
    I5 속도 크기가 물리 한계를 넘지 않는다
    I6 제자리회전은 정말 제자리다
    I2 STOP 은 모든 속도를 0으로 만든다
"""

import math

import harness  # noqa: F401  (PYTHONPATH 설정)
from domain.ports.baseline_ports import HostCommand
from domain.task import motion as M


def check(name, ok, detail=""):
    mark = "PASS" if ok else "**FAIL**"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    return ok


def run():
    print("A2/A4 — resolve_motion (D1 클램프 · D2 회전순수성)")
    results = []
    cap = M.AGREED_LINEAR_MPS
    rcap = M.AGREED_ROTATION_RAD_S

    # I5 — 극단 직진이 합의 크기로 잘리고 방향은 보존
    d = M.resolve_motion(HostCommand("APPROACH", linear_x=1000.0))
    results.append(check("I5 직진 1000→클램프", d.ok and abs(d.motion.linear_x - cap) < 1e-9,
                         f"linear_x={d.motion.linear_x}"))
    d = M.resolve_motion(HostCommand("APPROACH", linear_x=-1000.0))
    results.append(check("I5 후진 방향 보존", d.motion.linear_x < 0 and abs(d.motion.linear_x + cap) < 1e-9,
                         f"linear_x={d.motion.linear_x}"))
    d = M.resolve_motion(HostCommand("APPROACH", angular_z=999.0))
    results.append(check("I5 회전 999→클램프", abs(d.motion.angular_z - rcap) < 1e-9,
                         f"angular_z={d.motion.angular_z}"))

    # I5 — inf / nan (JSON 이 실어 나를 수 있는 값)
    d = M.resolve_motion(HostCommand("APPROACH", linear_x=float("inf")))
    results.append(check("I5 inf→클램프", math.isfinite(d.motion.linear_x) and abs(d.motion.linear_x) <= cap + 1e-9,
                         f"linear_x={d.motion.linear_x}"))
    d = M.resolve_motion(HostCommand("APPROACH", linear_x=float("nan")))
    finite = math.isfinite(d.motion.linear_x)
    results.append(check("I5 nan→유한값이어야", finite,
                         f"linear_x={d.motion.linear_x}  (nan 이 새면 베이스로 그대로 갈 위험)"))

    # I6 — 제자리회전에 병진이 섞이면 거부 + 정지
    d = M.resolve_motion(HostCommand("APPROACH", linear_x=0.1, angular_z=0.25))
    results.append(check("I6 회전+병진 거부", (not d.ok) and d.motion.is_stop, d.reason[:40]))

    # I2 — stop 이 나머지를 이긴다
    d = M.resolve_motion(HostCommand("APPROACH", linear_x=1000.0, stop=True))
    results.append(check("I2 stop 우선", d.ok and d.motion.is_stop))

    # 바구니 접근 구간은 더 낮은 상한
    d = M.resolve_motion(HostCommand("APPROACH_BOX", linear_x=1.0))
    results.append(check("I5 바구니접근 저속상한", abs(d.motion.linear_x - M.BASKET_APPROACH_MPS) < 1e-9,
                         f"linear_x={d.motion.linear_x}"))

    return results


if __name__ == "__main__":
    rs = run()
    print(f"\n{sum(rs)}/{len(rs)} 통과")
    raise SystemExit(0 if all(rs) else 1)

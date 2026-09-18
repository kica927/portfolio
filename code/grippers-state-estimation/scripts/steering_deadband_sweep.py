"""데드밴드 크기를 바꿔 가며(최대 명령 0.6) 조향 제어기 이점이 어떻게 변하는지 본다.
공칭 플랜트와 느린 플랜트(T0.8)에서 30°/90°/180° 정착시간 합과 최대 오버슈트, 전환 수 합을 비교한다."""
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import steering_compare as sc

DURATION = 15.0
TARGETS = (30, 90, 180)


def main():
    nominal = (0.02, 0.50, 0.935)
    plants = {"공칭 T0.5": (0.02, 0.50, 0.935), "느림 T0.8": (0.02, 0.80, 0.935)}
    sc.U_MAX = 0.6
    sc.BANG = 0.6
    print("최대 명령 0.6 · 제한 15s · 셀 = 정착시간 합(30+90+180°)s / 최대 오버슈트° / 전환 합 (실패 개수)")
    for db in (0.0, 0.1, 0.2, 0.35):
        sc.DEADBAND = db
        controllers = {"bang-bang ±0.6": sc.ctrl_bang, "비례 kp=1": sc.make_prop(1.0),
                       "비례 kp=2": sc.make_prop(2.0), "MPC": sc.make_mpc()}
        print(f"\n######## 데드밴드 {db} rad/s")
        print(f"{'제어기':16s}" + "".join(f"{p:>30s}" for p in plants))
        for cname, ctrl in controllers.items():
            cells = []
            for pp in plants.values():
                total, worst, sw_sum, fails = 0.0, 0.0, 0, 0
                for d in TARGETS:
                    st, ov, sw, _, _ = sc.run(ctrl, math.radians(d), pp, nominal, duration=DURATION)
                    if st is None:
                        fails += 1
                        st = DURATION
                    total += st
                    worst = max(worst, ov)
                    sw_sum += sw
                cells.append(f"{total:.1f} / {worst:.1f} / {sw_sum}" + (f" ({fails}실패)" if fails else ""))
            print(f"{cname:16s}" + "".join(f"{c:>30s}" for c in cells))


if __name__ == "__main__":
    main()

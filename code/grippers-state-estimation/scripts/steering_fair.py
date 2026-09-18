"""steering_compare.py 의 공정성 수정판: 모든 제어기의 최대 명령을 같게(0.4 세트 / 0.6 세트) 하고 제한 시간을 15초로 늘린다."""
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import steering_compare as sc

DURATION = 15.0
TARGETS = (30, 90, 180)


def main():
    nominal = (0.02, 0.50, 0.935)
    plants = {"공칭 T0.5 K0.93": (0.02, 0.50, 0.935), "느림 T0.8 K0.93": (0.02, 0.80, 0.935),
              "빠름 T0.3 K0.93": (0.02, 0.30, 0.935), "약함 T0.5 K0.80": (0.02, 0.50, 0.80)}
    print(f"허용 5° · 0.5s 유지 = 정착 · Host 10Hz · 데드밴드 {sc.DEADBAND} · 제한 {DURATION:.0f}s · 제어기는 공칭 모델 가정")
    print("셀 = 정착시간s / 오버슈트° / 명령전환  (정착 못 하면 '실패/최종오차°')")
    for umax in (0.4, 0.6):
        sc.U_MAX = umax
        sc.BANG = umax
        controllers = {f"bang-bang ±{umax}": sc.ctrl_bang, "비례 kp=1": sc.make_prop(1.0),
                       "비례 kp=2": sc.make_prop(2.0), "MPC": sc.make_mpc()}
        print(f"\n######## 최대 명령 {umax} rad/s")
        print(f"{'플랜트':18s}{'제어기':16s}" + "".join(f"{str(d) + '°':>22s}" for d in TARGETS))
        for pname, pp in plants.items():
            for cname, ctrl in controllers.items():
                cells = []
                for d in TARGETS:
                    st, ov, sw, ef, fe = sc.run(ctrl, math.radians(d), pp, nominal, duration=DURATION)
                    cells.append(f"실패/{fe:.1f}" if st is None else f"{st:.1f} / {ov:.1f} / {sw}")
                print(f"{pname:18s}{cname:16s}" + "".join(f"{c:>22s}" for c in cells))


if __name__ == "__main__":
    main()

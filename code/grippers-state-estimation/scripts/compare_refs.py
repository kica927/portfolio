"""사전 추정값·이동 임계값만 다르게 돌린 SLAM 기준 궤적끼리 얼마나 다른지 비교한다.
기준끼리 차이가 추정원들 사이의 차이보다 작아야 그 기준으로 추정원을 가를 수 있다."""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from eval_trajectories import GRID_HZ, align_initial, load_csv, resample, rpe, umeyama_se2, wrap


def main(base_path, others):
    b = load_csv(base_path)
    runs = {label: load_csv(p) for label, p in (o.split("=", 1) for o in others)}
    t0 = max([b["t"][0]] + [r["t"][0] for r in runs.values()])
    t1 = min([b["t"][-1]] + [r["t"][-1] for r in runs.values()])
    tq = np.arange(t0 + 1.0, t1 - 1.0, 1.0 / GRID_HZ)
    ref = resample(b["t"], b["map_x"], b["map_y"], b["map_yaw"], tq)
    print(f"기준 A = {base_path.split('/')[-1]} · 비교 구간 {tq[-1] - tq[0]:.1f}s")
    print(f"{'비교 대상':30s}{'ATE(m)':>10s}{'RPE1s 방향°':>13s}{'RPE5s 방향°':>13s}{'방향RMSE°':>12s}{'최종방향°':>11s}")
    for label, r in runs.items():
        est = align_initial(ref, resample(r["t"], r["map_x"], r["map_y"], r["map_yaw"], tq))
        aligned = umeyama_se2(np.c_[ref[0], ref[1]], np.c_[est[0], est[1]])
        ate = float(np.sqrt(np.mean(np.sum((aligned - np.c_[ref[0], ref[1]]) ** 2, axis=1))))
        e = wrap(est[2] - ref[2])
        print(f"{label:30s}{ate:10.3f}{rpe(ref, est, int(GRID_HZ))[1]:13.2f}{rpe(ref, est, int(5 * GRID_HZ))[1]:13.2f}"
              f"{np.degrees(np.sqrt(np.mean(e ** 2))):12.2f}{np.degrees(abs(e[-1])):11.2f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

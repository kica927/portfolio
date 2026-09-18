"""토크 모드 기록에서 궤적 종료 후 진동 주파수와 토크 부호 교대 비율을 구한다."""
import sys

import numpy as np

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]


def main(path, t_start):
    d = np.genfromtxt(path, delimiter=",", names=True)
    t = d["t"] - d["t"][0]
    dt = float(np.median(np.diff(t)))
    m = t >= t_start
    print(f"{path} · 샘플 주기 {dt * 1000:.2f}ms · 나이퀴스트 {0.5 / dt:.1f}Hz · 분석 구간 {t[m][0]:.1f}~{t[m][-1]:.1f}s")
    print(f"{'joint':14s}{'peak_Hz':>10s}{'vel_std':>10s}{'err_rms_mrad':>14s}{'vel_sign_flip/s':>17s}{'out_sign_flip_ratio':>21s}{'max|out|':>10s}")
    for j in JOINTS:
        v = d[f"vel_{j}"][m]
        e = d[f"err_{j}"][m]
        u = d[f"out_{j}"][m]
        v0 = v - v.mean()
        spec = np.abs(np.fft.rfft(v0 * np.hanning(len(v0))))
        f = np.fft.rfftfreq(len(v0), dt)
        k = int(np.argmax(spec[1:]) + 1)
        flips = np.sum(np.diff(np.sign(v0)) != 0) / (t[m][-1] - t[m][0])
        out_flip = float(np.mean(np.sign(u[1:]) * np.sign(u[:-1]) < 0))
        print(f"{j:14s}{f[k]:10.2f}{np.std(v):10.3f}{np.sqrt(np.mean(e ** 2)) * 1000:14.1f}{flips:17.1f}{out_flip:21.3f}{np.max(np.abs(u)):10.3f}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))

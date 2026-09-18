#!/usr/bin/env python3
"""hold_test 가 저장한 관절 위치 CSV 를 0.25초 간격으로 보여 주고, 샘플 간 위치 점프와 속도 크기 변화를 확인한다."""
import sys

import numpy as np

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]


def main(path):
    a = np.genfromtxt(path, delimiter=",", skip_header=1)
    t = a[:, 0] - a[0, 0]
    jump = np.abs(np.diff(a[:, 1:], axis=0)).max(1)
    k = int(jump.argmax())
    print(f"{path} · 샘플 {len(a)}개 · 기록 {t[-1]:.2f}s · 샘플 간 최대 위치 점프 {jump.max() * 1000:.2f} mrad (t={t[k + 1]:.3f}s)")
    print(f"{'t(s)':>7s}" + "".join(f"{j:>15s}" for j in ARM) + "   (첫 샘플 대비 mrad)")
    for tt in np.arange(0.0, t[-1] + 1e-9, 0.25):
        i = min(int(np.searchsorted(t, tt)), len(a) - 1)
        print(f"{t[i]:7.2f}" + "".join(f"{(a[i, 1 + j] - a[0, 1 + j]) * 1000:15.2f}" for j in range(5)))
    v = np.gradient(a[:, 1:], a[:, 0], axis=0)
    marks = [s for s in np.arange(0.0, t[-1] + 1e-9, 0.5)]
    print("최대 관절 속도(rad/s) 0.5s 간격: " + " ".join(
        f"{np.abs(v[min(int(np.searchsorted(t, s)), len(a) - 1)]).max():.4f}" for s in marks))


if __name__ == "__main__":
    main(sys.argv[1])

#!/usr/bin/env python3
"""track_test 기록 CSV 의 시간 범위 · 빈 구간 · 목표 궤적(ref)이 지나간 범위를 확인한다."""
import sys

import numpy as np

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]

for path in sys.argv[1:]:
    d = np.genfromtxt(path, delimiter=",", names=True)
    t = d["t"]
    gaps = np.diff(t)
    k = int(np.argmax(gaps))
    print(f"== {path.split('/')[-1]} · {len(t)}행 · {t[-1] - t[0]:.2f}s · 최대 빈 구간 {gaps.max() * 1000:.1f}ms (t={t[k] - t[0]:.2f}s)")
    print(f"   {'':10s}" + "".join(f"{j:>15s}" for j in JOINTS))
    print(f"   {'ref 시작':10s}" + "".join(f"{d['ref_' + j][0]:15.3f}" for j in JOINTS))
    print(f"   {'ref 최소':10s}" + "".join(f"{d['ref_' + j].min():15.3f}" for j in JOINTS))
    print(f"   {'ref 최대':10s}" + "".join(f"{d['ref_' + j].max():15.3f}" for j in JOINTS))
    print(f"   {'ref 끝':10s}" + "".join(f"{d['ref_' + j][-1]:15.3f}" for j in JOINTS))
    moving = np.any(np.abs(np.gradient(np.vstack([d["ref_" + j] for j in JOINTS]).T, t, axis=0)) > 1e-3, axis=1)
    edges = np.flatnonzero(np.diff(moving.astype(int)))
    print("   ref 가 움직인 구간(s): " + " ".join(f"{t[i + 1] - t[0]:.2f}" for i in edges))

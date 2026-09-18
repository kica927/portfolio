#!/usr/bin/env python3
"""관절 하나를 '관성 + PD + ZOH 샘플링' 모델로 보고 폐루프 극점 크기로 이산 안정성을 판정한다.

연속: I q'' = u,  u[k] = -P q[k-d] - D q'[k-d]  (d = 측정·계산 지연 스텝)
ZOH 로 이산화한 뒤 지연 상태를 붙여 폐루프 행렬의 최대 |고유값| 을 구한다. 1 보다 크면 불안정.
관성은 Pinocchio 질량행렬 대각값(자세별)을 쓴다.
"""
import os
import re

import numpy as np
import pinocchio as pin
import xacro
from ament_index_python.packages import get_package_share_directory

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
P = {"shoulder_pan": 5.0, "shoulder_lift": 5.0, "elbow_flex": 2.0, "wrist_flex": 0.15, "wrist_roll": 0.03}
D = {"shoulder_pan": 0.5, "shoulder_lift": 0.5, "elbow_flex": 0.2, "wrist_flex": 0.015, "wrist_roll": 0.003}
POSES = {"home": [0, 0, 0, 0, 0], "A": [0.8, -0.8, 0.9, 0.6, 0.5], "REST": [0.0, -1.4, 1.4, 1.0, 0.0]}
REST_FB_1K_PD = [0.033, -1.417, 1.461, 1.220, 0.584]
REST_ERR_1K_PD = [-0.03260, 0.01712, -0.06145, -0.22021, -0.58418]


def spectral_radius(inertia, p, d, T, delay):
    Ad = np.array([[1.0, T], [0.0, 1.0]])
    Bd = np.array([[T * T / (2 * inertia)], [T / inertia]])
    K = np.array([[p, d]])
    n = 2 * (delay + 1)
    A = np.zeros((n, n))
    A[0:2, 0:2] = Ad
    A[0:2, n - 2:n] = -Bd @ K
    for k in range(delay):
        A[2 * (k + 1):2 * (k + 2), 2 * k:2 * (k + 1)] = np.eye(2)
    if delay == 0:
        A = Ad - Bd @ K
    return float(np.max(np.abs(np.linalg.eigvals(A))))


def load():
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    model = pin.buildModelFromXML(urdf)
    return model, model.createData()


def main():
    model, data = load()
    iq = {n: model.joints[model.getJointId(n)].idx_q for n in ARM}
    print("폐루프 최대 |고유값| (1 초과 = 불안정)")
    print(f"{'자세':6s}{'주기':>7s}{'지연':>5s}" + "".join(f"{n:>15s}" for n in ARM))
    for label, pose in POSES.items():
        q = np.zeros(model.nq)
        for n, v in zip(ARM, pose):
            q[iq[n]] = v
        M = pin.crba(model, data, q)
        M = np.triu(M) + np.triu(M, 1).T
        inertia = {n: M[iq[n], iq[n]] for n in ARM}
        print(f"{label:6s}{'관성':>12s}" + "".join(f"{inertia[n]:15.6f}" for n in ARM))
        for hz in (100, 1000):
            for delay in (0, 1):
                rho = [spectral_radius(inertia[n], P[n], D[n], 1.0 / hz, delay) for n in ARM]
                print(f"{'':6s}{hz:>6d}Hz{delay:>5d}" + "".join(f"{r:15.3f}" + ("*" if r > 1 else " ") for r in rho).replace("  *", " *"))

    print("\n[REST 미스터리] 1kHz PD 가 실제로 멈춘 자세에서 P×오차 와 g(q) 비교")
    q = np.zeros(model.nq)
    for n, v in zip(ARM, REST_FB_1K_PD):
        q[iq[n]] = v
    g = pin.computeGeneralizedGravity(model, data, q)
    print(f"  {'':22s}" + "".join(f"{n:>15s}" for n in ARM))
    print(f"  {'P×오차 (N·m)':22s}" + "".join(f"{P[n] * e:15.4f}" for n, e in zip(ARM, REST_ERR_1K_PD)))
    print(f"  {'g(실제 자세) (N·m)':22s}" + "".join(f"{g[iq[n]]:15.4f}" for n in ARM))
    print(f"  {'차이 = 설명 안 되는 외력':22s}" + "".join(f"{P[n] * e - g[iq[n]]:15.4f}" for n, e in zip(ARM, REST_ERR_1K_PD)))


if __name__ == "__main__":
    main()

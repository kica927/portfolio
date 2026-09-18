#!/usr/bin/env python3
"""5관절 결합 모델로 100Hz/1kHz PD 의 이산 안정성을 판정한다.

M(q) q'' = u  (자세 q 에서 선형화, 중력·코리올리는 안정성 판정에서 제외)
u[k] = -P q[k] - D q'[k]  (대각 게인),  ZOH 샘플링.
관절 하나 모델과 달리 질량행렬의 비대각 결합을 포함한다.
또 실제로 멈춘 REST 자세에서 충돌 메시 최저점을 다시 계산한다.
"""
import os
import re
import sys

import numpy as np
import pinocchio as pin
import xacro
from ament_index_python.packages import get_package_share_directory
from scipy.linalg import expm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from floor_and_onset import lowest_points

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
P = np.diag([5.0, 5.0, 2.0, 0.15, 0.03])
D = np.diag([0.5, 0.5, 0.2, 0.015, 0.003])
HOME = np.zeros(5)
POSE_A = np.array([0.8, -0.8, 0.9, 0.6, 0.5])
REST = np.array([0.0, -1.4, 1.4, 1.0, 0.0])
REST_FB_1K_PD = np.array([0.033, -1.417, 1.461, 1.220, 0.584])


def rho(M5, hz):
    n = 5
    T = 1.0 / hz
    Minv = np.linalg.inv(M5)
    A = np.zeros((2 * n, 2 * n)); A[:n, n:] = np.eye(n)
    B = np.zeros((2 * n, n)); B[n:, :] = Minv
    big = np.zeros((3 * n, 3 * n)); big[:2 * n, :2 * n] = A; big[:2 * n, 2 * n:] = B
    E = expm(big * T)
    Ad, Bd = E[:2 * n, :2 * n], E[:2 * n, 2 * n:]
    K = np.hstack([P, D])
    lam = np.linalg.eigvals(Ad - Bd @ K)
    k = int(np.argmax(np.abs(lam)))
    return float(np.abs(lam[k])), lam[k]


def main():
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    model = pin.buildModelFromXML(urdf)
    data = model.createData()
    iq = [model.joints[model.getJointId(n)].idx_q for n in ARM]

    def mass5(q5):
        q = np.zeros(model.nq); q[iq] = q5
        M = pin.crba(model, data, q)
        M = np.triu(M) + np.triu(M, 1).T
        return M[np.ix_(iq, iq)]

    print("5관절 결합 모델 폐루프 최대 |고유값| (1 초과 = 불안정)")
    for label, q5 in (("home", HOME), ("A", POSE_A), ("REST", REST), ("REST 실제 정지자세", REST_FB_1K_PD)):
        M5 = mass5(q5)
        eff = 1.0 / np.diag(np.linalg.inv(M5))
        r100, l100 = rho(M5, 100)
        r1k, _ = rho(M5, 1000)
        freq = abs(np.angle(l100)) / (2 * np.pi) * 100
        print(f"  {label:18s} 100Hz {r100:.3f}{'*' if r100 > 1 else ' '} (진동 {freq:5.1f}Hz) · 1kHz {r1k:.3f}"
              f" · 결합 유효관성 {np.round(eff, 6)}")

    print("\nhome→A 5차 보간 경로를 따라 100Hz 극점 (궤적 0~1.0s)")
    for t in (0.0, 0.05, 0.1, 0.13, 0.2, 0.3, 0.5, 0.75, 1.0):
        s = 10 * t ** 3 - 15 * t ** 4 + 6 * t ** 5
        r, lam = rho(mass5(HOME + s * (POSE_A - HOME)), 100)
        print(f"  t={t:4.2f}s  |λ|max={r:.3f}{'*' if r > 1 else ' '}  진동 {abs(np.angle(lam)) / (2 * np.pi) * 100:5.1f}Hz")

    share_root = os.path.dirname(get_package_share_directory("so101_moveit_config"))
    for label, q5 in (("REST 목표", REST), ("REST 실제 정지자세", REST_FB_1K_PD)):
        q = np.zeros(model.nq); q[iq] = q5
        low = sorted(lowest_points(model, data, urdf, share_root, q), key=lambda r: r[1])[:3]
        print(f"[{label}] 최저 충돌 메시 점: " + " · ".join(f"{n} {z * 100:+.2f}cm" for n, z in low))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Pinocchio 로 SO-101 중력 토크 g(q) 와 질량행렬을 계산해, Gazebo PD 실측 유지 오차와 비교한다.

PD 평형에서 P*(ref - fb) = g(fb) 이므로 유지 오차 ref - fb 를 고정점 반복으로 예측할 수 있다.
예측이 실측과 맞으면 Pinocchio 모델이 Gazebo 와 같은 동역학이라는 뜻이다.
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
I_GUESS = {"shoulder_pan": 0.023, "shoulder_lift": 0.023, "elbow_flex": 0.0087, "wrist_flex": 0.00063, "wrist_roll": 0.0001}
CASES = {
    "A":    ([0.8, -0.8, 0.9, 0.6, 0.5],   [-0.00, -29.71, -183.47, -292.16, -14.33]),
    "REST": ([0.0, -1.4, 1.4, 1.0, 0.0],   [-32.60, 17.12, -61.45, -220.21, -584.18]),
}


def load_model():
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    return pin.buildModelFromXML(urdf)


def main():
    model = load_model()
    data = model.createData()
    iq = {n: model.joints[model.getJointId(n)].idx_q for n in ARM + ["gripper"]}
    print(f"모델 관절 {model.nq}개: {[model.names[i] for i in range(1, model.njoints)]}")
    print(f"총 질량 {sum(inert.mass for inert in model.inertias):.3f} kg · 중력 {model.gravity.linear}")

    for label, (pose, measured) in CASES.items():
        qd = np.zeros(model.nq)
        for n, v in zip(ARM, pose):
            qd[iq[n]] = v
        g_des = pin.computeGeneralizedGravity(model, data, qd).copy()
        q = qd.copy()
        for _ in range(100):
            g = pin.computeGeneralizedGravity(model, data, q)
            for n in ARM:
                q[iq[n]] = qd[iq[n]] - g[iq[n]] / P[n]
        pred = [(qd[iq[n]] - q[iq[n]]) * 1000 for n in ARM]
        M = pin.crba(model, data, qd)
        M = np.triu(M) + np.triu(M, 1).T
        print(f"\n[자세 {label}] q_d = {pose}")
        print(f"  {'':26s}" + "".join(f"{n:>15s}" for n in ARM))
        print(f"  {'g(q_d) 중력토크 (N·m)':26s}" + "".join(f"{g_des[iq[n]]:15.4f}" for n in ARM))
        print(f"  {'예측 유지오차 (mrad)':26s}" + "".join(f"{v:15.2f}" for v in pred))
        print(f"  {'Gazebo 실측 (mrad)':26s}" + "".join(f"{v:15.2f}" for v in measured))
        print(f"  {'M 대각 = 관절 관성':26s}" + "".join(f"{M[iq[n], iq[n]]:15.6f}" for n in ARM))
        print(f"  {'처음 어림한 관성':26s}" + "".join(f"{I_GUESS[n]:15.6f}" for n in ARM))
        print(f"  {'100Hz 이산 지표 D·dt/I':26s}" + "".join(f"{D[n] * 0.01 / M[iq[n], iq[n]]:15.2f}" for n in ARM))
        print(f"  {'1kHz 이산 지표 D·dt/I':26s}" + "".join(f"{D[n] * 0.001 / M[iq[n], iq[n]]:15.3f}" for n in ARM))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""자세 A 에서 중력 보상 토크가 1ms 빠졌을 때 생기는 관절 속도(Δq' = -M^-1 g · dt)를 예측하고,
전환 실험 기록에서 측정한 킥 직후 관절 속도와 관절별로 비교한다."""
import os
import re
import sys

import numpy as np
import pinocchio as pin
import xacro
from ament_index_python.packages import get_package_share_directory

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
POSE_A = [0.8, -0.8, 0.9, 0.6, 0.5]
DT = 0.001


def main(hold_csv):
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    model = pin.buildModelFromXML(urdf)
    data = model.createData()
    iq = [model.joints[model.getJointId(n)].idx_q for n in ARM]
    q = np.zeros(model.nq)
    q[iq] = POSE_A
    M = pin.crba(model, data, q)
    M = np.triu(M) + np.triu(M, 1).T
    g = pin.computeGeneralizedGravity(model, data, q)[iq]
    pred = -np.linalg.solve(M[np.ix_(iq, iq)], g) * DT

    a = np.genfromtxt(hold_csv, delimiter=",", skip_header=1)
    t = a[:, 0]
    effort = a[:, 6:11]
    zero_rows = np.where(np.all(np.abs(effort) < 1e-9, axis=1))[0]
    k0 = int(zero_rows[0])
    v = np.gradient(a[:, 1:6], t, axis=0)
    k50 = int(np.searchsorted(t, t[k0] + 0.05))
    print(f"토크 0 샘플 시각 {t[k0] - t[0]:.3f}s · 개수 {len(zero_rows)}")
    print(f"{'':30s}" + "".join(f"{j:>15s}" for j in ARM))
    print(f"{'예측 Δq̇ = -M⁻¹g·1ms (rad/s)':30s}" + "".join(f"{x:15.4f}" for x in pred))
    print(f"{'측정 킥 50ms 후 속도 (rad/s)':30s}" + "".join(f"{x:15.4f}" for x in v[k50]))


if __name__ == "__main__":
    main(sys.argv[1])

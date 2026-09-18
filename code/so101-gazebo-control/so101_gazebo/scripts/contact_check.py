#!/usr/bin/env python3
"""track_test 가 기록한 실제 관절 궤적(fb)을 따라 충돌 메시 최저점을 계산해, 실행 중 바닥 접촉이 있었는지 사후 검사한다."""
import os
import re
import sys

import numpy as np
import pinocchio as pin
import xacro
from ament_index_python.packages import get_package_share_directory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from floor_and_onset import lowest_points

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
IGNORE = {"base_link"}


def main(paths):
    share_root = os.path.dirname(get_package_share_directory("so101_moveit_config"))
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    model = pin.buildModelFromXML(urdf)
    data = model.createData()
    iq = [model.joints[model.getJointId(n)].idx_q for n in ARM]
    for path in paths:
        d = np.genfromtxt(path, delimiter=",", names=True)
        t = d["t"] - d["t"][0]
        step = max(1, int(round(0.02 / float(np.median(np.diff(t))))))
        worst = (np.inf, None, None)
        for k in range(0, len(t), step):
            q = np.zeros(model.nq)
            q[iq] = [d[f"fb_{j}"][k] for j in ARM]
            rows = [r for r in lowest_points(model, data, urdf, share_root, q) if r[0] not in IGNORE]
            name, z = min(rows, key=lambda r: r[1])
            if z < worst[0]:
                worst = (z, name, t[k])
        verdict = "접촉 의심" if worst[0] < 0.002 else "접촉 없음"
        print(f"  {os.path.basename(path):34s} 최저 {worst[0] * 100:+6.2f}cm ({worst[1]}, t={worst[2]:.2f}s) → {verdict}")


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""바닥에 닿지 않는 두 번째 테스트 자세를 고른다 (바닥에 고정된 base_link 는 판정에서 뺀다).

후보마다 (1) 목표 자세 (2) PD(1kHz, 적분 없음)로 중력에 처졌을 때의 예상 평형 자세
두 경우의 충돌 메시 최저점을 계산한다. 처진 자세까지 여유가 있어야 PD·PID·중력보상 비교가 접촉 없이 공정하다.
"""
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
P = np.array([5.0, 5.0, 2.0, 0.15, 0.03])
POSE_A = np.array([0.8, -0.8, 0.9, 0.6, 0.5])
CANDIDATES = {
    "REST(기존)":  [0.0, -1.4, 1.4, 1.0, 0.0],
    "B1":          [0.0, -1.0, 1.0, 0.6, 0.0],
    "B2":          [-0.6, -1.0, 1.2, 0.3, -0.5],
    "B3":          [-0.6, -0.6, 1.2, 0.5, -0.5],
    "B4":          [-0.8, -0.4, 0.8, 0.8, -0.8],
    "B5":          [-0.6, 0.2, 0.6, 0.6, -0.5],
    "B6":          [-0.6, -1.1, 1.0, 0.2, -0.5],
    "B7":          [-0.6, -1.2, 0.9, 0.0, -0.5],
    "B8":          [0.0, -1.1, 0.8, 0.2, 0.0],
}


def main():
    share_root = os.path.dirname(get_package_share_directory("so101_moveit_config"))
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    model = pin.buildModelFromXML(urdf)
    data = model.createData()
    iq = [model.joints[model.getJointId(n)].idx_q for n in ARM]

    def full(q5):
        q = np.zeros(model.nq); q[iq] = q5
        return q

    def sag(q5):
        q = np.array(q5, float)
        for _ in range(200):
            g = pin.computeGeneralizedGravity(model, data, full(q))[iq]
            q = 0.5 * q + 0.5 * (np.array(q5) - g / P)
        return q

    def lowest(q5):
        return min((r for r in lowest_points(model, data, urdf, share_root, full(q5)) if r[0] != "base_link"), key=lambda r: r[1])

    print(f"{'후보':12s}{'목표 최저점':>22s}{'PD 처짐 후 최저점':>28s}{'A 로부터 이동량(rad)':>22s}   처짐량 mrad")
    for label, q5 in CANDIDATES.items():
        lo_t = lowest(q5)
        qs = sag(q5)
        lo_s = lowest(qs)
        move = np.abs(np.array(q5) - POSE_A).sum()
        print(f"{label:12s}{lo_t[0]:>14s} {lo_t[1] * 100:+6.2f}cm{lo_s[0]:>20s} {lo_s[1] * 100:+6.2f}cm{move:22.2f}   "
              + " ".join(f"{v:+.0f}" for v in (np.array(q5) - qs) * 1000))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""(1) 테스트 자세에서 충돌 메시의 가장 낮은 점 높이를 계산해 바닥 접촉 여부를 본다.
(2) 100Hz PD 기록에서 토크 부호 교대 진동이 시작된 시각을 찾는다.
"""
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pinocchio as pin
import xacro
from ament_index_python.packages import get_package_share_directory

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
POSES = {"home": [0, 0, 0, 0, 0], "A": [0.8, -0.8, 0.9, 0.6, 0.5], "REST": [0.0, -1.4, 1.4, 1.0, 0.0]}


def read_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[80:84])[0]
    if 84 + 50 * n == len(data):
        tri = np.frombuffer(data, dtype=np.uint8, offset=84, count=50 * n).reshape(n, 50)
        v = np.frombuffer(tri[:, 12:48].tobytes(), dtype="<f4").reshape(-1, 3)
        return v.astype(float)
    verts = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)
    return np.array(verts, dtype=float)


def origin_se3(el):
    if el is None:
        return pin.SE3.Identity()
    xyz = [float(v) for v in el.get("xyz", "0 0 0").split()]
    rpy = [float(v) for v in el.get("rpy", "0 0 0").split()]
    return pin.SE3(pin.rpy.rpyToMatrix(*rpy), np.array(xyz))


def lowest_points(model, data, urdf, share_root, q):
    pin.framesForwardKinematics(model, data, q)
    root = ET.fromstring(urdf)
    cache, rows = {}, []
    for link in root.findall("link"):
        name = link.get("name")
        if not model.existFrame(name):
            continue
        oMl = data.oMf[model.getFrameId(name)]
        zmin = np.inf
        for col in link.findall("collision"):
            mesh = col.find("geometry/mesh")
            if mesh is None:
                continue
            fn = mesh.get("filename").replace("package://", share_root + "/")
            if fn not in cache:
                cache[fn] = read_stl(fn)
                scale = mesh.get("scale")
                if scale:
                    cache[fn] = cache[fn] * np.array([float(s) for s in scale.split()])
            col_origin = origin_se3(col.find("origin"))
            local = (col_origin.rotation @ cache[fn].T).T + col_origin.translation
            w = (oMl.rotation @ local.T).T + oMl.translation
            zmin = min(zmin, float(w[:, 2].min()))
        if np.isfinite(zmin):
            rows.append((name, zmin))
    return rows


def onset(csv_path):
    d = np.genfromtxt(csv_path, delimiter=",", names=True)
    t = d["t"] - d["t"][0]
    win = 25
    print(f"\n== 100Hz 진동 시작 시각 ({csv_path.rsplit('/', 1)[-1]}, 0.25s 창에서 토크 부호 교대 비율 > 0.8 첫 시각)")
    print("   궤적: 0~1.0s home→A 이동 · 1.0~3.0s A 유지 · 3.0~4.5s A→REST 이동 · 4.5~6.5s REST 유지")
    for j in ARM:
        u = d[f"out_{j}"]
        flip = (np.sign(u[1:]) * np.sign(u[:-1]) < 0).astype(float)
        ratio = np.convolve(flip, np.ones(win) / win, mode="valid")
        idx = np.where(ratio > 0.8)[0]
        first = f"{t[idx[0]]:.2f}s" if len(idx) else "없음"
        print(f"   {j:14s} 진동 시작 {first}")


def main():
    share_root = os.path.dirname(get_package_share_directory("so101_moveit_config"))
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    model = pin.buildModelFromXML(urdf)
    data = model.createData()
    iq = {n: model.joints[model.getJointId(n)].idx_q for n in ARM}
    for label, pose in POSES.items():
        q = np.zeros(model.nq)
        for n, v in zip(ARM, pose):
            q[iq[n]] = v
        rows = lowest_points(model, data, urdf, share_root, q)
        low = sorted(rows, key=lambda r: r[1])[:3]
        print(f"[자세 {label}] 가장 낮은 충돌 메시 점: " + " · ".join(f"{n} {z * 100:+.1f}cm" for n, z in low))
    onset(sys.argv[1])


if __name__ == "__main__":
    main()

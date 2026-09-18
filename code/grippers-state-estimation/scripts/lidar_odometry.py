"""연속 스캔 2D ICP 로 LiDAR 오도메트리를 만들고, 정면 방향·실제 전진 속도·회전 부호를 검증한다."""
import sys
import csv
import math

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
from scipy.spatial import cKDTree

SELF_OCCLUSION_R = 0.12
MAX_R = 8.0
BIAS = {"run_20260905_150105": 0.00376, "run_20260905_151233": 0.00393}
H_NOMINAL = 0.07 + 0.0925


def read(uri):
    topics = ["/scan_raw", "/cmd_vel", "/ros_robot_controller/imu_raw"]
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
    classes = {t: get_message(types[t]) for t in topics}
    scans, ct, cv, it, gz = [], [], [], [], []
    while reader.has_next():
        topic, data, stamp = reader.read_next()
        m = deserialize_message(data, classes[topic])
        t = stamp / 1e9
        if topic == "/scan_raw":
            r = np.asarray(m.ranges, dtype=float)
            a = m.angle_min + m.angle_increment * np.arange(len(r))
            scans.append((t, r, a))
        elif topic == "/cmd_vel":
            ct.append(t); cv.append((m.linear.x, m.angular.z))
        else:
            it.append(t); gz.append(m.angular_velocity.z)
    return scans, np.array(ct), np.array(cv), np.array(it), np.array(gz)


def to_xy(r, a):
    ok = np.isfinite(r) & (r > SELF_OCCLUSION_R) & (r < MAX_R)
    return np.c_[r[ok] * np.cos(a[ok]), r[ok] * np.sin(a[ok])]


def icp(src, tgt, iters=30):
    tree = cKDTree(tgt)
    R, t = np.eye(2), np.zeros(2)
    for i in range(iters):
        p = src @ R.T + t
        d, j = tree.query(p)
        thr = max(0.05, 0.3 * (1 - i / iters))
        m = d < thr
        if m.sum() < 30:
            return None
        A, B = p[m], tgt[j[m]]
        ca, cb = A.mean(0), B.mean(0)
        U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
        Ri = Vt.T @ U.T
        if np.linalg.det(Ri) < 0:
            Vt[1] *= -1
            Ri = Vt.T @ U.T
        R, t = Ri @ R, Ri @ t + (cb - Ri @ ca)
    d, _ = tree.query(src @ R.T + t)
    inl = d < 0.05
    return R, t, float(np.mean(inl)), float(np.sqrt(np.mean(d[inl] ** 2))) if inl.any() else float("nan")


def main(uri):
    name = uri.rstrip("/").split("/")[-1]
    scans, ct, cv, it, gz = read(uri)
    gz = gz - BIAS[name]
    xy = [to_xy(r, a) for _, r, a in scans]
    st = np.array([s[0] for s in scans])

    rows = []
    pose = np.eye(3)
    traj = [(st[0], 0.0, 0.0, 0.0, float("nan"), float("nan"))]
    fails = 0
    for k in range(len(scans) - 1):
        res = icp(xy[k + 1], xy[k])
        if res is None:
            fails += 1
            res = (np.eye(2), np.zeros(2), float("nan"), float("nan"))
        R, t, inl, rms = res
        dth = math.atan2(R[1, 0], R[0, 0])
        inc = np.eye(3); inc[:2, :2] = R; inc[:2, 2] = t
        pose = pose @ inc
        traj.append((st[k + 1], pose[0, 2], pose[1, 2], math.atan2(pose[1, 0], pose[0, 0]), inl, rms))

        m = (it >= st[k]) & (it < st[k + 1])
        d_imu = float(np.sum(gz[m]) * np.median(np.diff(it))) if m.any() else float("nan")
        ci = np.searchsorted(ct, st[k] - 0.5, side="right") - 1
        cj = np.searchsorted(ct, st[k + 1], side="right") - 1
        steady = ci >= 0 and np.all(cv[ci:cj + 1] == cv[cj])
        rows.append((st[k + 1] - st[k], t[0], t[1], dth, inl, rms, d_imu, tuple(cv[cj]) if cj >= 0 else (0.0, 0.0), steady))

    with open(f"results/{name}_lidar_odom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "x", "y", "yaw", "inlier", "rms"])
        w.writerows(traj)

    dt = np.array([r[0] for r in rows]); tx = np.array([r[1] for r in rows]); ty = np.array([r[2] for r in rows])
    dth = np.array([r[3] for r in rows]); inl = np.array([r[4] for r in rows]); dimu = np.array([r[6] for r in rows])
    cmd = np.array([r[7] for r in rows]); steady = np.array([r[8] for r in rows])

    print(f"==== {name} · 스캔쌍 {len(rows)}개 · ICP 실패 {fails}개 · 인라이어 비율 중앙값 {np.nanmedian(inl):.3f}"
          f" · 5% 분위 {np.nanpercentile(inl, 5):.3f}")

    ok = np.isfinite(dimu) & np.isfinite(inl) & (inl > 0.5)
    s = float(np.dot(dth[ok], dimu[ok]) / np.dot(dimu[ok], dimu[ok]))
    c = float(np.corrcoef(dth[ok], dimu[ok])[0, 1])
    print(f"  회전 증분 ICP vs IMU: 기울기 {s:+.3f} · 상관 {c:+.3f} · 총합 ICP {np.sum(dth[ok]):+.3f} rad / IMU {np.sum(dimu[ok]):+.3f} rad")

    fwd = ok & steady & np.isclose(cmd[:, 0], 0.1) & np.isclose(cmd[:, 1], 0.0) & (np.abs(dimu) < 0.01)
    if fwd.sum() >= 5:
        ang = np.degrees(np.arctan2(ty[fwd], tx[fwd]))
        vec = np.array([np.mean(np.cos(np.radians(ang))), np.mean(np.sin(np.radians(ang)))])
        heading = math.degrees(math.atan2(vec[1], vec[0])) % 360
        speed = np.hypot(tx[fwd], ty[fwd]) / dt[fwd]
        print(f"  정상 직진 스캔쌍 {int(fwd.sum())}개 · LiDAR 프레임에서 로봇 전진 방향 {heading:.1f}° "
              f"(방향 집중도 {np.hypot(*vec):.3f}) · 실제 속도 중앙값 {np.median(speed):.4f} m/s "
              f"(IQR {np.percentile(speed, 25):.4f}~{np.percentile(speed, 75):.4f}) · 명령 0.1")
    else:
        heading = None
        print(f"  정상 직진 스캔쌍 부족: {int(fwd.sum())}개")

    still = ok & steady & np.all(cmd == 0, axis=1)
    if still.any():
        print(f"  정지 스캔쌍 {int(still.sum())}개 · ICP 병진 크기 중앙값 {np.median(np.hypot(tx[still], ty[still])) * 1000:.2f}mm"
              f" · 회전 표준편차 {np.degrees(np.std(dth[still])):.3f}°  (ICP 노이즈 바닥)")

    T = np.array(traj)
    print(f"  LiDAR 오도메트리 누적: 경로 길이 {np.sum(np.hypot(np.diff(T[:, 1]), np.diff(T[:, 2]))):.2f}m · "
          f"시작→끝 변위 {np.hypot(T[-1, 1], T[-1, 2]):.3f}m · x 범위 {np.ptp(T[:, 1]):.2f}m · y 범위 {np.ptp(T[:, 2]):.2f}m")

    if heading is not None:
        rel_rows = []
        for t_s, r, a in scans:
            rel = (np.degrees(a) - heading + 180) % 360 - 180
            rel_rows.append((rel, r))
        print("  정면 기준 각도별 거리 분포 (상대각: 유효율 / p50 / p95 / 최대, 11.3° 바닥 교차 시 상한)")
        for lo in range(-90, 90, 20):
            vals = np.concatenate([r[(rel >= lo) & (rel < lo + 20) & np.isfinite(r) & (r > SELF_OCCLUSION_R)] for rel, r in rel_rows])
            tot = sum(int(np.sum((rel >= lo) & (rel < lo + 20))) for rel, _ in rel_rows)
            mid = math.radians(lo + 10)
            bound = H_NOMINAL / math.tan(math.radians(11.3)) / max(math.cos(mid), 1e-3)
            print(f"    {lo:+4d}~{lo + 20:+4d}°: {len(vals) / max(tot, 1):.2f} / {np.median(vals):.3f} / "
                  f"{np.percentile(vals, 95):.3f} / {vals.max():.3f}   (상한 {bound:.3f})")
        occl = []
        for rel, r in rel_rows[:200]:
            occl.append(rel[np.isfinite(r) & (r > 0) & (r <= SELF_OCCLUSION_R)])
        occl = np.concatenate(occl)
        if len(occl):
            print(f"  자기가림(≤{SELF_OCCLUSION_R}m) 점의 정면 기준 각도 범위: {np.percentile(occl, 2):.1f}° ~ {np.percentile(occl, 98):.1f}°")


if __name__ == "__main__":
    main(sys.argv[1])

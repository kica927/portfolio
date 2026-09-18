"""SLAM 지도 포즈를 기준으로 명령 오도메트리·EKF 구성·IMU 적분의 위치/방향 오차를 평가한다.

기준 궤적(SLAM)도 추정값이므로 '정답'이 아니라 LiDAR 스캔매칭 기반 기준이라는 한계가 있다.
지표:
  ATE  : SE(2) 최소제곱 정렬(스케일 없음) 후 위치 RMSE
  RPE  : Δt 동안의 상대 변위·상대 회전 오차 RMSE (기준이 거의 안 움직인 창은 제외)
  초기 정렬 후 최종 위치/방향 오차, 방향 RMSE
"""
import argparse
import csv
import math

import numpy as np

GRID_HZ = 20.0
MIN_MOVE = 0.01
MIN_TURN = math.radians(2.0)


def load_csv(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(x[k]) for x in rows]) for k in rows[0]}


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def resample(t, x, y, yaw, tq):
    return np.interp(tq, t, x), np.interp(tq, t, y), np.interp(tq, t, np.unwrap(yaw))


def align_initial(ref, est):
    rx, ry, ryaw = ref
    ex, ey, eyaw = est
    d = ryaw[0] - eyaw[0]
    c, s = math.cos(d), math.sin(d)
    px, py = ex - ex[0], ey - ey[0]
    return rx[0] + c * px - s * py, ry[0] + s * px + c * py, eyaw + d


def umeyama_se2(ref_xy, est_xy):
    mr, me = ref_xy.mean(0), est_xy.mean(0)
    U, _, Vt = np.linalg.svd((est_xy - me).T @ (ref_xy - mr))
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[1] *= -1
        R = Vt.T @ U.T
    return (est_xy - me) @ R.T + mr


def moving_windows(ref, n):
    rx, ry, ryaw = ref
    for k in range(0, len(rx) - n, max(1, n // 2)):
        c, s = math.cos(-ryaw[k]), math.sin(-ryaw[k])
        dx, dy = rx[k + n] - rx[k], ry[k + n] - ry[k]
        tr = np.array([c * dx - s * dy, s * dx + c * dy])
        rr = ryaw[k + n] - ryaw[k]
        if np.linalg.norm(tr) < MIN_MOVE and abs(rr) < MIN_TURN:
            continue
        yield k, tr, rr


def rpe(ref, est, n):
    ex, ey, eyaw = est
    et, er = [], []
    for k, tr, rr in moving_windows(ref, n):
        c, s = math.cos(-eyaw[k]), math.sin(-eyaw[k])
        dx, dy = ex[k + n] - ex[k], ey[k + n] - ey[k]
        te = np.array([c * dx - s * dy, s * dx + c * dy])
        et.append(np.linalg.norm(tr - te))
        er.append(wrap(rr - (eyaw[k + n] - eyaw[k])))
    if not et:
        return float("nan"), float("nan"), 0
    return float(np.sqrt(np.mean(np.square(et)))), float(np.degrees(np.sqrt(np.mean(np.square(er))))), len(et)


def yaw_rpe(ref, yaw, n):
    e = [wrap((yaw[k + n] - yaw[k]) - rr) for k, _, rr in moving_windows(ref, n)]
    return float(np.degrees(np.sqrt(np.mean(np.square(e))))) if e else float("nan")


def imu_yaw(bag, bias):
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=bag, storage_id="sqlite3"), rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    topic = "/ros_robot_controller/imu_raw"
    reader.set_filter(rosbag2_py.StorageFilter(topics=[topic]))
    cls = get_message(types[topic])
    t, gz = [], []
    while reader.has_next():
        _, data, _ = reader.read_next()
        m = deserialize_message(data, cls)
        t.append(m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)
        gz.append(m.angular_velocity.z - bias)
    t, gz = np.array(t), np.array(gz)
    return t, np.concatenate([[0.0], np.cumsum(0.5 * (gz[1:] + gz[:-1]) * np.diff(t))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slam", required=True)
    ap.add_argument("--ekf", nargs="*", default=[], help="라벨=경로")
    ap.add_argument("--bag", default="")
    ap.add_argument("--imu-bias", type=float, default=0.0)
    ap.add_argument("--odom-label", default="명령 오도메트리(/odom_raw)", help="SLAM 기록의 odom 열(그 실행의 사전 추정값) 이름")
    args = ap.parse_args()

    s = load_csv(args.slam)
    t0, t1 = s["t"][0], s["t"][-1]
    sources = {args.odom_label: (s["t"], s["odom_x"], s["odom_y"], s["odom_yaw"])}
    for item in args.ekf:
        label, path = item.split("=", 1)
        e = load_csv(path)
        sources[f"EKF {label}"] = (e["t"], e["x"], e["y"], e["yaw"])
        t0, t1 = max(t0, e["t"][0]), min(t1, e["t"][-1])
    tq = np.arange(t0 + 1.0, t1 - 1.0, 1.0 / GRID_HZ)
    ref = resample(s["t"], s["map_x"], s["map_y"], s["map_yaw"], tq)

    corr = np.hypot(np.interp(tq, s["t"], s["map_x"] - s["odom_x"]), np.interp(tq, s["t"], s["map_y"] - s["odom_y"]))
    path_len = float(np.sum(np.hypot(np.diff(ref[0]), np.diff(ref[1]))))
    n1, n5 = int(GRID_HZ), int(5 * GRID_HZ)
    moving1 = sum(1 for _ in moving_windows(ref, n1))
    print(f"평가 구간 {tq[-1] - tq[0]:.1f}s · 기준(SLAM) 경로 {path_len:.2f}m · 누적 회전 {np.degrees(np.sum(np.abs(np.diff(ref[2])))):.0f}°"
          f" · 1s 이동 창 {moving1}개")
    print(f"SLAM 보정량(map−odom) 최대 {corr.max():.3f}m · 50ms 간 최대 점프 {np.abs(np.diff(corr)).max() * 100:.1f}cm")

    cols = ["ATE(m)", "RPE1s 위치cm", "RPE1s 방향°", "RPE5s 위치cm", "RPE5s 방향°", "최종위치m", "최종방향°", "방향RMSE°", "경로m"]
    print(f"{'추정원':28s}" + "".join(f"{c:>14s}" for c in cols))
    for label, (t, x, y, yaw) in sources.items():
        est = align_initial(ref, resample(t, x, y, yaw, tq))
        aligned = umeyama_se2(np.c_[ref[0], ref[1]], np.c_[est[0], est[1]])
        ate = float(np.sqrt(np.mean(np.sum((aligned - np.c_[ref[0], ref[1]]) ** 2, axis=1))))
        r1, r5 = rpe(ref, est, n1), rpe(ref, est, n5)
        yaw_err = wrap(est[2] - ref[2])
        vals = [ate, r1[0] * 100, r1[1], r5[0] * 100, r5[1],
                float(np.hypot(est[0][-1] - ref[0][-1], est[1][-1] - ref[1][-1])),
                float(np.degrees(abs(yaw_err[-1]))), float(np.degrees(np.sqrt(np.mean(yaw_err ** 2)))),
                float(np.sum(np.hypot(np.diff(est[0]), np.diff(est[1]))))]
        print(f"{label:28s}" + "".join(f"{v:14.3f}" for v in vals))

    if args.bag:
        ti, yi = imu_yaw(args.bag, args.imu_bias)
        yaw_imu = np.interp(tq, ti, yi)
        yaw_imu = yaw_imu - yaw_imu[0] + ref[2][0]
        err = wrap(yaw_imu - ref[2])
        vals = ["-", "-", f"{yaw_rpe(ref, yaw_imu, n1):.3f}", "-", f"{yaw_rpe(ref, yaw_imu, n5):.3f}", "-",
                f"{np.degrees(abs(err[-1])):.3f}", f"{np.degrees(np.sqrt(np.mean(err ** 2))):.3f}", "-"]
        print(f"{'IMU 자이로 적분(방향만)':28s}" + "".join(f"{v:>14s}" for v in vals))


if __name__ == "__main__":
    main()

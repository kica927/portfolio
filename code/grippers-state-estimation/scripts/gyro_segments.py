"""명령이 일정한 구간별로 IMU 자이로 z 평균을 구해, 명령 대비 실제 회전 비율과 정지 노이즈를 측정한다."""
import sys

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

SETTLE = 0.3


def read(uri, topics):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
    classes = {t: get_message(types[t]) for t in topics}
    out = {t: [] for t in topics}
    while reader.has_next():
        topic, data, stamp = reader.read_next()
        out[topic].append((stamp / 1e9, deserialize_message(data, classes[topic])))
    return out


def segments(ct, cv, t_end):
    segs = []
    start = 0
    for i in range(1, len(ct) + 1):
        if i == len(ct) or not np.allclose(cv[i], cv[start]):
            end_t = ct[i] if i < len(ct) else t_end
            segs.append((ct[start], end_t, tuple(np.round(cv[start], 3))))
            start = i
    return segs


def main(uri):
    d = read(uri, ["/cmd_vel", "/ros_robot_controller/imu_raw"])
    ct = np.array([t for t, _ in d["/cmd_vel"]])
    cv = np.array([(m.linear.x, m.angular.z) for _, m in d["/cmd_vel"]])
    it = np.array([t for t, _ in d["/ros_robot_controller/imu_raw"]])
    gz = np.array([m.angular_velocity.z for _, m in d["/ros_robot_controller/imu_raw"]])

    segs = segments(ct, cv, it[-1])
    print("  명령 구간 수:", len(segs), " 종류별 개수:",
          {k: sum(1 for s in segs if s[2] == k) for k in sorted({s[2] for s in segs})})

    def seg_stats(kind, min_len):
        rows = []
        for t0, t1, v in segs:
            if v != kind or t1 - t0 < min_len:
                continue
            m = (it >= t0 + SETTLE) & (it < t1)
            if m.sum() >= 10:
                rows.append((t1 - t0, float(np.mean(gz[m])), float(np.std(gz[m])), int(m.sum())))
        return np.array(rows) if rows else np.empty((0, 4))

    still = seg_stats((0.0, 0.0), 2.0)
    bias = float(np.average(still[:, 1], weights=still[:, 3])) if len(still) else 0.0
    print(f"  정지 구간(>=2s) {len(still)}개 · 바이어스 {bias:.5f} rad/s · 구간 내 표준편차 중앙값 "
          f"{np.median(still[:, 2]):.4f} · 구간 평균의 흩어짐 {np.std(still[:, 1]):.5f}")

    fwd = seg_stats((0.1, 0.0), 1.0)
    if len(fwd):
        print(f"  직진 구간(>=1s) {len(fwd)}개 · 바이어스 보정 자이로 평균 중앙값 {np.median(fwd[:, 1] - bias):.4f} rad/s"
              f" · 표준편차 중앙값 {np.median(fwd[:, 2]):.4f}")

    for w in (0.4, -0.4):
        rot = seg_stats((0.0, w), 1.0)
        if not len(rot):
            continue
        ratio = (rot[:, 1] - bias) / w
        print(f"  회전 {w:+.1f} 구간(>=1s) {len(rot)}개 · 지속 중앙값 {np.median(rot[:, 0]):.2f}s · "
              f"실제/명령 비율 중앙값 {np.median(ratio):.3f} (IQR {np.percentile(ratio, 25):.3f}~{np.percentile(ratio, 75):.3f})"
              f" · 표준편차 중앙값 {np.median(rot[:, 2]):.4f}")
    rot_all = np.vstack([seg_stats((0.0, w), 1.0) for w in (0.4, -0.4)])
    if len(rot_all):
        long_mask = rot_all[:, 0] >= 3.0
        print(f"  지속 3초 이상 회전 구간 {int(long_mask.sum())}개의 |실제/명령| 중앙값:",
              round(float(np.median(np.abs(rot_all[long_mask, 1] - bias) / 0.4)), 3) if long_mask.any() else "없음")


if __name__ == "__main__":
    for uri in sys.argv[1:]:
        print("====", uri)
        main(uri)

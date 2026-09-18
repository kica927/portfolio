"""EKF 출력 yaw 의 누적 회전량을 IMU 단순 적분과 비교해, EKF 가 회전 측정을 얼마나 반영하지 못했는지 본다.
EKF 출력 샘플 간격 분포도 함께 본다(간격이 벌어지면 처리 지연·누락 신호)."""
import csv
import sys

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def imu(bag, bias):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=bag, storage_id="sqlite3"), rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    topic = "/ros_robot_controller/imu_raw"
    reader.set_filter(rosbag2_py.StorageFilter(topics=[topic]))
    cls = get_message(types[topic])
    t, g = [], []
    while reader.has_next():
        _, data, _ = reader.read_next()
        m = deserialize_message(data, cls)
        t.append(m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)
        g.append(m.angular_velocity.z - bias)
    return np.array(t), np.array(g)


def main(bag, bias, paths):
    ti, gi = imu(bag, bias)
    for path in paths:
        with open(path) as f:
            rows = list(csv.DictReader(f))
        t = np.array([float(r["t"]) for r in rows])
        yaw = np.unwrap([float(r["yaw"]) for r in rows])
        m = (ti >= t[0]) & (ti <= t[-1])
        dt = np.diff(ti[m])
        g = gi[m]
        imu_abs = float(np.sum(np.abs(0.5 * (g[1:] + g[:-1])) * dt))
        imu_net = float(np.sum(0.5 * (g[1:] + g[:-1]) * dt))
        gaps = np.diff(t)
        print(f"{path.split('/')[-1]:44s} 누적|회전| EKF {np.degrees(np.sum(np.abs(np.diff(yaw)))):7.0f}° / IMU {np.degrees(imu_abs):7.0f}°"
              f" (비율 {np.sum(np.abs(np.diff(yaw))) / imu_abs:.3f}) · 순회전 EKF {np.degrees(yaw[-1] - yaw[0]):+7.0f}° / IMU {np.degrees(imu_net):+7.0f}°"
              f" · 출력 간격 중앙 {np.median(gaps) * 1000:.1f}ms, 99% {np.percentile(gaps, 99) * 1000:.1f}ms, 최대 {gaps.max() * 1000:.0f}ms")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), sys.argv[3:])

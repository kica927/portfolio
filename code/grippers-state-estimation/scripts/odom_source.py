"""/odom_raw 가 휠 인코더 측정인지, 명령(/cmd_vel)을 그대로 적분한 것인지 판별한다."""
import sys
import math

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


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


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def main(uri):
    d = read(uri, ["/cmd_vel", "/odom_raw", "/joint_states", "/ros_robot_controller/imu_raw"])

    ct = np.array([t for t, _ in d["/cmd_vel"]])
    cv = np.array([(m.linear.x, m.angular.z) for _, m in d["/cmd_vel"]])
    ot = np.array([t for t, _ in d["/odom_raw"]])
    ov = np.array([(m.twist.twist.linear.x, m.twist.twist.angular.z) for _, m in d["/odom_raw"]])
    oyaw = np.unwrap([yaw_of(m.pose.pose.orientation) for _, m in d["/odom_raw"]])

    print("==== 값의 종류")
    print("  cmd_vel 고유값 개수:", len({tuple(np.round(v, 4)) for v in cv}))
    print("  odom twist 고유값 개수:", len({tuple(np.round(v, 4)) for v in ov}))
    print("  odom twist 고유값 예시:", sorted({tuple(np.round(v, 4)) for v in ov})[:12])
    cmd_set = {tuple(np.round(v, 4)) for v in cv}
    print("  odom twist 가 명령값 집합 안에 있는 비율:",
          round(float(np.mean([tuple(np.round(v, 4)) in cmd_set for v in ov])), 4))

    print("==== 시간 지연별 일치율 (odom 시각보다 lag 초 이전의 최신 명령과 같은가)")
    best = None
    for lag in [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]:
        idx = np.searchsorted(ct, ot - lag, side="right") - 1
        ok = idx >= 0
        match = np.all(np.isclose(ov[ok], cv[idx[ok]], atol=1e-4), axis=1)
        rate = float(np.mean(match))
        print(f"  lag {lag:.2f}s : {rate:.4f}")
        best = max(best or (0, 0), (rate, lag))
    print("  최고 일치:", best)

    print("==== odom 자세 변화 vs odom twist 적분")
    dt = np.diff(ot)
    yaw_from_twist = np.concatenate([[0], np.cumsum(ov[:-1, 1] * dt)])
    print("  odom yaw 총변화(rad):", round(float(oyaw[-1] - oyaw[0]), 4),
          " twist 적분(rad):", round(float(yaw_from_twist[-1]), 4))
    print("  누적 회전량 |dyaw| 합 — pose:", round(float(np.sum(np.abs(np.diff(oyaw)))), 3),
          " twist:", round(float(np.sum(np.abs(ov[:-1, 1]) * dt)), 3))

    print("==== IMU 자이로 z 적분 vs odom yaw")
    it = np.array([t for t, _ in d["/ros_robot_controller/imu_raw"]])
    gz = np.array([m.angular_velocity.z for _, m in d["/ros_robot_controller/imu_raw"]])
    cidx = np.searchsorted(ct, it, side="right") - 1
    still = (cidx >= 0) & np.all(np.isclose(cv[np.clip(cidx, 0, None)], 0, atol=1e-6), axis=1)
    bias = float(np.mean(gz[still])) if still.any() else 0.0
    print("  정지 명령 구간 샘플 수:", int(still.sum()), " 자이로 z 평균(바이어스):", round(bias, 5),
          " 표준편차:", round(float(np.std(gz[still])), 5))
    idt = np.diff(it)
    imu_yaw = np.concatenate([[0], np.cumsum((gz[:-1] - bias) * idt)])
    print("  IMU yaw 총변화(rad, 바이어스 보정):", round(float(imu_yaw[-1]), 4),
          " 보정 전:", round(float(np.sum(gz[:-1] * idt)), 4))
    print("  누적 회전량 |dyaw| 합 — IMU:", round(float(np.sum(np.abs(gz[:-1] - bias) * idt)), 3))
    turning = np.abs(np.interp(it, ot, ov[:, 1])) > 0.2
    if turning.any():
        ratio = gz[turning] - bias
        ref = np.interp(it[turning], ot, ov[:, 1])
        print("  회전 중(|wz|>0.2) 자이로/odom 비율 중앙값:", round(float(np.median(ratio / ref)), 3),
              " 샘플:", int(turning.sum()))

    print("==== /joint_states")
    js = d["/joint_states"]
    names = list(js[0][1].name)
    pos = np.array([list(m.position) for _, m in js if len(m.position) == len(names)])
    vel = [list(m.velocity) for _, m in js]
    print("  이름:", names, " 메시지:", len(js), " velocity 비어있음:", all(len(v) == 0 for v in vel))
    print("  position 첫값:", np.round(pos[0], 3), " 마지막:", np.round(pos[-1], 3))
    print("  position 이 한 번이라도 변하는 관절:", [n for n, c in zip(names, np.ptp(pos, 0)) if c > 1e-6])


if __name__ == "__main__":
    main(sys.argv[1])

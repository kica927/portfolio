"""bag의 프레임 구조와 센서 특성을 조사한다."""
import sys
import math
import collections
import xml.etree.ElementTree as ET

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def quat_to_rpy_deg(x, y, z, w):
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return tuple(round(math.degrees(a), 2) for a in (roll, pitch, yaw))


def open_reader(uri, topics):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
    return reader, types


def main(uri):
    wanted = ["/tf_static", "/tf", "/odom_raw", "/ros_robot_controller/imu_raw",
              "/scan_raw", "/cmd_vel", "/robot_description"]
    reader, types = open_reader(uri, wanted)
    classes = {t: get_message(types[t]) for t in wanted if t in types}

    static_tf = {}
    dyn_tf = collections.Counter()
    odom = {"frames": set(), "pose": [], "twist": [], "cov_pose": None, "cov_twist": None, "t": []}
    imu = {"frames": set(), "ori_cov0": set(), "gyro_z": [], "acc": [], "ori": [], "t": []}
    scan = {"frames": set(), "meta": None, "valid": [], "t": []}
    cmd = []
    urdf = None

    while reader.has_next():
        topic, data, stamp = reader.read_next()
        msg = deserialize_message(data, classes[topic])
        if topic == "/tf_static":
            for tr in msg.transforms:
                r = tr.transform.rotation
                p = tr.transform.translation
                static_tf[(tr.header.frame_id, tr.child_frame_id)] = (
                    (round(p.x, 4), round(p.y, 4), round(p.z, 4)), quat_to_rpy_deg(r.x, r.y, r.z, r.w))
        elif topic == "/tf":
            for tr in msg.transforms:
                dyn_tf[(tr.header.frame_id, tr.child_frame_id)] += 1
        elif topic == "/odom_raw":
            odom["frames"].add((msg.header.frame_id, msg.child_frame_id))
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            odom["pose"].append((p.x, p.y, quat_to_rpy_deg(q.x, q.y, q.z, q.w)[2]))
            tw = msg.twist.twist
            odom["twist"].append((tw.linear.x, tw.linear.y, tw.angular.z))
            odom["cov_pose"] = [msg.pose.covariance[i * 7] for i in range(6)]
            odom["cov_twist"] = [msg.twist.covariance[i * 7] for i in range(6)]
            odom["t"].append(stamp)
        elif topic == "/ros_robot_controller/imu_raw":
            imu["frames"].add(msg.header.frame_id)
            imu["ori_cov0"].add(round(msg.orientation_covariance[0], 6))
            imu["gyro_z"].append(msg.angular_velocity.z)
            a = msg.linear_acceleration
            imu["acc"].append((a.x, a.y, a.z))
            q = msg.orientation
            imu["ori"].append((q.x, q.y, q.z, q.w))
            imu["t"].append(stamp)
        elif topic == "/scan_raw":
            scan["frames"].add(msg.header.frame_id)
            if scan["meta"] is None:
                scan["meta"] = dict(angle_min=round(math.degrees(msg.angle_min), 2),
                                    angle_max=round(math.degrees(msg.angle_max), 2),
                                    inc_deg=round(math.degrees(msg.angle_increment), 4),
                                    n=len(msg.ranges), range_min=msg.range_min, range_max=msg.range_max,
                                    scan_time=msg.scan_time)
            r = np.asarray(msg.ranges)
            scan["valid"].append(float(np.mean(np.isfinite(r) & (r > msg.range_min) & (r < msg.range_max))))
            scan["t"].append(stamp)
        elif topic == "/cmd_vel":
            cmd.append((msg.linear.x, msg.linear.y, msg.angular.z))
        elif topic == "/robot_description":
            urdf = msg.data

    def rate(ts):
        return round((len(ts) - 1) / ((ts[-1] - ts[0]) / 1e9), 2) if len(ts) > 1 else 0

    print("==== /tf_static (parent -> child : xyz / rpy deg)")
    for k, v in sorted(static_tf.items()):
        print(f"  {k[0]} -> {k[1]} : {v[0]} / {v[1]}")
    print("==== /tf 동적 변환 (parent -> child : 개수)")
    for k, v in dyn_tf.most_common():
        print(f"  {k[0]} -> {k[1]} : {v}")

    print("==== /odom_raw")
    op = np.array(odom["pose"]); ot = np.array(odom["twist"])
    print("  frames:", odom["frames"], " rate Hz:", rate(odom["t"]))
    print("  pose cov diag:", odom["cov_pose"], " twist cov diag:", odom["cov_twist"])
    print("  첫 pose (x,y,yaw):", np.round(op[0], 3), " 마지막 pose:", np.round(op[-1], 3))
    print("  x 범위:", np.round([op[:, 0].min(), op[:, 0].max()], 3), " y 범위:", np.round([op[:, 1].min(), op[:, 1].max()], 3))
    print("  twist vx/vy/wz 최소:", np.round(ot.min(0), 3), " 최대:", np.round(ot.max(0), 3))
    print("  vy 가 0이 아닌 비율:", round(float(np.mean(np.abs(ot[:, 1]) > 1e-3)), 3))

    print("==== /imu_raw")
    ia = np.array(imu["acc"]); iq = np.array(imu["ori"])
    print("  frames:", imu["frames"], " rate Hz:", rate(imu["t"]), " orientation_cov[0] 값:", imu["ori_cov0"])
    print("  orientation 전부 0 인가:", bool(np.allclose(iq, 0)), " 첫 쿼터니언:", np.round(iq[0], 4))
    print("  가속도 평균 (x,y,z):", np.round(ia.mean(0), 3), " 크기:", round(float(np.linalg.norm(ia.mean(0))), 3))
    g = ia.mean(0)
    print("  평균 중력벡터로 본 기울기 roll/pitch deg:",
          round(math.degrees(math.atan2(g[1], g[2])), 2), round(math.degrees(math.atan2(-g[0], math.hypot(g[1], g[2]))), 2))
    print("  gyro_z 평균/표준편차:", round(float(np.mean(imu["gyro_z"])), 5), round(float(np.std(imu["gyro_z"])), 5))

    print("==== /scan_raw")
    print("  frames:", scan["frames"], " rate Hz:", rate(scan["t"]), " meta:", scan["meta"])
    print("  유효 거리 비율 평균:", round(float(np.mean(scan["valid"])), 3))

    print("==== /cmd_vel")
    c = np.array(cmd)
    print("  vx/vy/wz 최소:", np.round(c.min(0), 3), " 최대:", np.round(c.max(0), 3))
    print("  vy 명령이 0이 아닌 비율:", round(float(np.mean(np.abs(c[:, 1]) > 1e-3)), 3))

    if urdf:
        print("==== URDF joint (센서·베이스 관련)")
        root = ET.fromstring(urdf)
        for j in root.findall("joint"):
            child = j.find("child").get("link")
            parent = j.find("parent").get("link")
            o = j.find("origin")
            xyz = o.get("xyz") if o is not None else None
            rpy = o.get("rpy") if o is not None else None
            if any(k in (child + parent).lower() for k in ("lidar", "laser", "imu", "base", "camera", "depth")):
                rpy_deg = [round(math.degrees(float(v)), 2) for v in rpy.split()] if rpy else None
                print(f"  {j.get('name')} [{j.get('type')}] {parent} -> {child} xyz={xyz} rpy_deg={rpy_deg}")


if __name__ == "__main__":
    main(sys.argv[1])

"""/odom_raw 공분산이 속도 상태(정지·회전·직진)에 따라 어떻게 바뀌는지, IMU 공분산은 얼마인지 센다."""
import collections
import sys

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def main(bags):
    topics = ["/odom_raw", "/ros_robot_controller/imu_raw"]
    for bag in bags:
        reader = rosbag2_py.SequentialReader()
        reader.open(rosbag2_py.StorageOptions(uri=bag, storage_id="sqlite3"), rosbag2_py.ConverterOptions("cdr", "cdr"))
        types = {t.name: t.type for t in reader.get_all_topics_and_types()}
        reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
        cls = {t: get_message(types[t]) for t in topics}
        table = collections.Counter()
        imu = collections.Counter()
        while reader.has_next():
            topic, data, _ = reader.read_next()
            m = deserialize_message(data, cls[topic])
            if topic == "/odom_raw":
                vx, wz = round(m.twist.twist.linear.x, 3), round(m.twist.twist.angular.z, 3)
                state = "정지" if vx == 0 and wz == 0 else ("회전" if wz != 0 else "직진")
                table[(state, m.twist.covariance[35], m.twist.covariance[0], m.pose.covariance[35])] += 1
            else:
                imu[(round(m.angular_velocity_covariance[8], 6), round(m.linear_acceleration_covariance[0], 6))] += 1
        print(f"==== {bag.rstrip('/').split('/')[-1]}")
        print("  odom 속도 상태 / twist 공분산 yaw_rate / twist 공분산 vx / pose 공분산 yaw : 개수")
        for (state, cw, cv, cp), n in sorted(table.items()):
            print(f"    {state}  {cw:g} / {cv:g} / {cp:g} : {n}")
        print("  IMU 공분산 (angular_velocity z, linear_acceleration x) : 개수 ->", dict(imu))


if __name__ == "__main__":
    main(sys.argv[1:])

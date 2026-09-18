"""/ekf/odom 을 CSV 로 기록한다."""
import csv
import math
import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from nav_msgs.msg import Odometry


class EkfLogger(Node):
    def __init__(self, path):
        super().__init__("ekf_logger")
        self.file = open(path, "w", newline="")
        self.writer = csv.writer(self.file)
        self.writer.writerow(["t", "x", "y", "yaw", "vx", "wz"])
        self.create_subscription(Odometry, "/ekf/odom", self.on_odom, 200)

    def on_odom(self, msg):
        q = msg.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        p = msg.pose.pose.position
        self.writer.writerow([stamp, p.x, p.y, yaw, msg.twist.twist.linear.x, msg.twist.twist.angular.z])


def main():
    rclpy.init()
    node = EkfLogger(sys.argv[1])
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.file.close()


if __name__ == "__main__":
    main()

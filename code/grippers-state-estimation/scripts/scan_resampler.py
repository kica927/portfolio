"""점 개수가 스캔마다 달라지는 /scan_raw 를 1° 간격 360점으로 고정해 /scan_fixed 로 다시 발행한다.

slam_toolbox(Karto)는 첫 스캔의 점 개수를 기준으로 삼아, 개수가 다른 스캔을 거부한다.
"""
import math

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

BINS = 360


class ScanResampler(Node):
    def __init__(self):
        super().__init__("scan_resampler")
        self.pub = self.create_publisher(LaserScan, "/scan_fixed", 50)
        self.create_subscription(LaserScan, "/scan_raw", self.on_scan, 50)

    def on_scan(self, msg):
        r = np.asarray(msg.ranges, dtype=float)
        ok = np.isfinite(r) & (r > msg.range_min) & (r < msg.range_max)
        ang = (msg.angle_min + msg.angle_increment * np.arange(len(r))) % (2 * math.pi)
        b = np.floor(np.degrees(ang)).astype(int) % BINS
        out = np.full(BINS, np.inf)
        np.minimum.at(out, b[ok], r[ok])
        fixed = LaserScan()
        fixed.header = msg.header
        fixed.angle_min = 0.0
        fixed.angle_increment = 2 * math.pi / BINS
        fixed.angle_max = fixed.angle_increment * (BINS - 1)
        fixed.time_increment = msg.scan_time / BINS if msg.scan_time > 0 else 0.0
        fixed.scan_time = msg.scan_time
        fixed.range_min = msg.range_min
        fixed.range_max = msg.range_max
        fixed.ranges = out.astype(np.float32).tolist()
        self.pub.publish(fixed)


def main():
    rclpy.init()
    node = ScanResampler()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()

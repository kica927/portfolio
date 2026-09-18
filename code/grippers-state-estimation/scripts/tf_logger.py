"""map -> base_footprint 와 odom -> base_footprint 를 주기적으로 조회해 CSV 로 기록한다."""
import csv
import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class TfLogger(Node):
    def __init__(self, path):
        super().__init__("tf_logger", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.file = open(path, "w", newline="")
        self.writer = csv.writer(self.file)
        self.writer.writerow(["t", "map_x", "map_y", "map_yaw", "odom_x", "odom_y", "odom_yaw"])
        self.last = None
        self.create_timer(0.05, self.tick)

    def tick(self):
        now = self.get_clock().now()
        if now.nanoseconds == 0:
            return
        try:
            m = self.buffer.lookup_transform("map", "base_footprint", Time())
            o = self.buffer.lookup_transform("odom", "base_footprint", Time())
        except Exception:
            return
        stamp = o.header.stamp.sec + o.header.stamp.nanosec * 1e-9
        if stamp == self.last:
            return
        self.last = stamp
        mt, ot = m.transform, o.transform
        self.writer.writerow([stamp, mt.translation.x, mt.translation.y, yaw_of(mt.rotation),
                              ot.translation.x, ot.translation.y, yaw_of(ot.rotation)])


def main():
    rclpy.init()
    node = TfLogger(sys.argv[1])
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.file.close()


if __name__ == "__main__":
    main()

"""/odom_raw 를 odom -> base_footprint TF 로 발행한다 (녹화 bag 에는 이 TF 가 없다)."""
import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.parameter import Parameter
from tf2_ros import TransformBroadcaster


class OdomToTf(Node):
    def __init__(self):
        super().__init__("odom_to_tf", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.br = TransformBroadcaster(self)
        self.create_subscription(Odometry, "/odom_raw", self.on_odom, 100)

    def on_odom(self, msg):
        tf = TransformStamped()
        tf.header.stamp = msg.header.stamp
        tf.header.frame_id = "odom"
        tf.child_frame_id = "base_footprint"
        p = msg.pose.pose.position
        tf.transform.translation.x = p.x
        tf.transform.translation.y = p.y
        tf.transform.rotation = msg.pose.pose.orientation
        self.br.sendTransform(tf)


def main():
    rclpy.init()
    node = OdomToTf()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()

"""IMU 자이로 z 바이어스를 빼서 /imu_corrected 로 다시 발행한다.

robot_localization 은 자이로 바이어스를 추정하지 않으므로, 정지 구간에서 측정한 바이어스를 미리 빼 주지 않으면
544초 동안 약 117° 의 방향 드리프트가 그대로 EKF 에 들어간다.
"""
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu


class ImuBiasCorrect(Node):
    def __init__(self):
        super().__init__("imu_bias_correct")
        self.bias = self.declare_parameter("bias_z", 0.0).value
        self.pub = self.create_publisher(Imu, "/imu_corrected", 100)
        self.create_subscription(Imu, "/ros_robot_controller/imu_raw", self.on_imu, 100)
        self.get_logger().info(f"자이로 z 바이어스 {self.bias:.5f} rad/s 보정")

    def on_imu(self, msg):
        msg.angular_velocity.z -= self.bias
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = ImuBiasCorrect()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()

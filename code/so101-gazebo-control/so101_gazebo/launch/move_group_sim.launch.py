"""so101_moveit_config 설정 그대로 move_group 을 시뮬레이션 시간으로 띄운다 (원본 launch 는 use_sim_time 인자가 없다)."""
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("so101", package_name="so101_moveit_config").to_moveit_configs()
    return LaunchDescription([
        Node(package="moveit_ros_move_group", executable="move_group", output="screen",
             parameters=[moveit_config.to_dict(), {"use_sim_time": True, "publish_robot_description_semantic": True}]),
    ])

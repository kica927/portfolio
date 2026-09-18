"""SO-101 을 Gazebo Harmonic 에 헤드리스로 띄우고 ros2_control 컨트롤러를 올린다.

원본 so101_moveit_config 의 URDF 를 그대로 읽어, mock 하드웨어 블록만 gz_ros2_control 블록으로
바꾸고 world 고정 관절을 붙인다. 원본 패키지는 수정하지 않는다.
"""
import os
import re

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, OpaqueFunction,
                            RegisterEventHandler, SetEnvironmentVariable)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

ARM_JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
GRIPPER_JOINT = "gripper"


def build_urdf(control_mode, effort_limit, controllers_yaml):
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = xacro.process_file(src).toxml()
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", urdf, flags=re.S)
    if effort_limit:
        urdf = re.sub(r'effort="[0-9.eE+-]+"', f'effort="{effort_limit}"', urdf)

    joints = []
    for name in ARM_JOINTS + [GRIPPER_JOINT]:
        command = control_mode if name in ARM_JOINTS else "position"
        joints.append(
            f'<joint name="{name}">'
            f'<command_interface name="{command}"/>'
            '<state_interface name="position"><param name="initial_value">0.0</param></state_interface>'
            '<state_interface name="velocity"/>'
            '<state_interface name="effort"/>'
            '</joint>')

    sim_block = (
        '<link name="world"/>'
        '<joint name="world_fixed" type="fixed"><parent link="world"/><child link="base_link"/></joint>'
        '<ros2_control name="so101_gz" type="system">'
        '<hardware><plugin>gz_ros2_control/GazeboSimSystem</plugin></hardware>'
        + "".join(joints) +
        '</ros2_control>'
        '<gazebo><plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">'
        f'<parameters>{controllers_yaml}</parameters>'
        '</plugin></gazebo>')
    return urdf.replace("</robot>", sim_block + "</robot>")


def setup(context):
    share = get_package_share_directory("so101_gazebo")
    control_mode = LaunchConfiguration("control_mode").perform(context)
    effort_limit = LaunchConfiguration("effort_limit").perform(context)
    controllers = LaunchConfiguration("controllers").perform(context) or \
        os.path.join(share, "config", f"controllers_{control_mode}.yaml")
    world = os.path.join(share, "worlds", "arm_world.sdf")
    urdf = build_urdf(control_mode, effort_limit, controllers)

    gz = ExecuteProcess(cmd=["gz", "sim", "-s", "-r", "-v", "2", world], output="screen")
    bridge = Node(package="ros_gz_bridge", executable="parameter_bridge",
                  arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"], output="screen")
    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
               parameters=[{"robot_description": urdf, "use_sim_time": True}], output="screen")
    spawn = Node(package="ros_gz_sim", executable="create",
                 arguments=["-topic", "robot_description", "-name", "so101", "-z", "0.0"], output="screen")

    def spawner(name):
        return Node(package="controller_manager", executable="spawner",
                    arguments=[name, "--controller-manager", "/controller_manager",
                               "--controller-manager-timeout", "60"], output="screen")

    jsb = spawner("joint_state_broadcaster")
    arm_names = [n for n in LaunchConfiguration("arm_controllers").perform(context).split(",") if n]
    arm = Node(package="controller_manager", executable="spawner",
               arguments=arm_names + ["--controller-manager", "/controller_manager",
                                      "--controller-manager-timeout", "60"], output="screen")
    gripper = spawner("gripper_controller")

    return [
        gz, bridge, rsp, spawn,
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[jsb])),
        RegisterEventHandler(OnProcessExit(target_action=jsb, on_exit=[arm, gripper])),
    ]


def generate_launch_description():
    resource_root = os.path.dirname(get_package_share_directory("so101_moveit_config"))
    return LaunchDescription([
        DeclareLaunchArgument("control_mode", default_value="position",
                              description="팔 관절 명령 인터페이스: position 또는 effort"),
        DeclareLaunchArgument("effort_limit", default_value="",
                              description="URDF 관절 토크 한계(N·m) 덮어쓰기. 비우면 원본 값"),
        DeclareLaunchArgument("arm_controllers", default_value="arm_controller",
                              description="팔에 스폰할 컨트롤러(콤마 구분, 체인은 하위부터). 예: gravity_compensation,arm_controller"),
        DeclareLaunchArgument("controllers", default_value="",
                              description="컨트롤러 설정 yaml 경로. 비우면 controllers_<mode>.yaml"),
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH",
                               os.pathsep.join(filter(None, [os.environ.get("GZ_SIM_RESOURCE_PATH", ""), resource_root]))),
        SetEnvironmentVariable("GZ_SIM_SYSTEM_PLUGIN_PATH",
                               os.pathsep.join(filter(None, [os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", ""), "/opt/ros/jazzy/lib"]))),
        OpaqueFunction(function=setup),
    ])

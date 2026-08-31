# so101_moveit_config

SO-ARM101 (SO-101) 용 MoveIt 2 설정 패키지 — mock 하드웨어 데모.

## 구성
- URDF: soarm_lab so101_new_calib 기반 (transmission 제거, mesh package:// 경로, mock ros2_control 추가)
- planning group: `arm` (shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll / tip=gripper_frame_link), `gripper`
- 플래너: OMPL + Pilz industrial motion planner
- 실행: ros2_control `mock_components/GenericSystem` + joint_trajectory_controller (arm / gripper)

## 빌드
```
cd ~/so101_ws
colcon build --packages-select so101_moveit_config
source install/setup.bash
```

## 실행 (데스크탑 화면 앞에서, RViz 포함)
```
source /opt/ros/jazzy/setup.bash
source ~/so101_ws/install/setup.bash
ros2 launch so101_moveit_config demo.launch.py
```
RViz의 MotionPlanning 패널에서 목표 자세를 드래그 → Plan → Execute.
group state 프리셋: arm=`home`,`rest` / gripper=`open`,`closed`.

## 헤드리스 검증 (SSH)
```
ros2 launch so101_moveit_config demo.launch.py use_rviz:=false
```
로그에 "You can start planning now!" 와 arm/gripper controller "Configured and activated" 확인.

## 다음 단계 (실기 연동, 2026-09-08 전 하드웨어 필요)
mock 대신 Feetech STS3215 용 ros2_control SystemInterface 를 작성해 교체하면 실제 팔에서 MoveIt 궤적 실행 가능. 기존 arm_driver_node / teleop 툴의 시리얼 통신 코드를 재활용하는 것이 지름길.

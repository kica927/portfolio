# MoveIt 2 — SO-ARM101 모션 플래닝 (시뮬)

> *2026 · 단독 · 로봇팔 트랙 확장*
>
> [SO-ARM101 로봇팔 트랙](soarm-robotarm-track.md)의 팔을 **MoveIt 2**로 올려, URDF에서
> 충돌 회피·IK 기반 모션 플래닝까지 되는 설정 패키지를 만들고 **하드웨어 없이 헤드리스로
> 동작을 검증**했다. 실기 팔이 없어도 성립하는, 순수 소프트웨어 산출물이다.

---

## Problem

그동안 SO-ARM101은 lerobot 텔레오퍼레이션(리더-팔로워)과 자체 IK 스크립트로만 움직였다.
**표준 모션 플래닝 스택(MoveIt 2)** 위에 올리면 충돌 인지 계획·다중 플래너·RViz 인터랙션이
가능해진다. 관건은 실기 팔 없이 이 스택을 **검증 가능한 형태로** 세우는 것.

## Method — config 패키지 구성

기존 SO-101 URDF(onshape-to-robot 생성)를 MoveIt 입력으로 가공:
- 구식 `<transmission>` 블록 제거, mesh 경로를 `package://` 로 정규화
- **mock 하드웨어**(`ros2_control` `mock_components/GenericSystem`) 삽입 → 실기 없이 실행

MoveIt 설정(Setup Assistant GUI 없이 파일로 직접 작성):

| 요소 | 내용 |
|---|---|
| planning group `arm` | shoulder_pan · shoulder_lift · elbow_flex · wrist_flex · wrist_roll (5축), tip=gripper_frame_link |
| planning group `gripper` | gripper (1축) |
| IK | KDLKinematicsPlugin |
| 플래너 | OMPL + Pilz industrial motion planner |
| 실행 | joint_trajectory_controller(arm/gripper) + joint_state_broadcaster |
| 조인트 한계 | URDF 실값(예: shoulder_pan ±1.92 rad) |

환경: Ubuntu 24.04 · **ROS 2 Jazzy** · `ros-jazzy-moveit`.

## Verification (헤드리스, 실기 0)

SSH만으로 GUI 없이 검증:
- **xacro → URDF** 파싱 성공(16 KB flat URDF), mesh 13개 참조 유효
- **MoveItConfigsBuilder** 로드 성공(robot_description·SRDF·kinematics, planning group 2개)
- `move_group` 기동 — Plan/Cartesian/Kinematics/Execute 등 전 서비스 로드, **OMPL·Pilz 파이프라인
  로드**, 로그에 `You can start planning now!`
- `ros2_control` mock 하드웨어 + **컨트롤러 3종 모두 "Configured and activated"**
  (joint_state_broadcaster · arm_controller · gripper_controller), 종료 후 잔여 프로세스 0

## Results

실기 팔 없이 **SO-ARM101 모션 플래닝 스택이 완전히 기동·플래닝 준비 완료** 상태까지 도달.
RViz MotionPlanning 패널에서 목표 자세 → Plan → Execute(mock)가 가능하며, group state
프리셋(arm `home`/`rest`, gripper `open`/`closed`)을 넣어 두었다.

## 리더 암 / 팔로워 암

MoveIt config는 **SO-101 URDF 하나**로 돌아가므로 리더·팔로워 **기구학이 동일** — 플래닝·시뮬은
팔 구분이 없다. 실기 구동만 대상 팔의 토크·포트·캘리브레이션이 다를 뿐이다.

## Limitations

- **mock 하드웨어**다. 실제 STS3215 서보 구동은 별도의 `ros2_control` SystemInterface가 필요하며
  (기존 arm_driver/teleop의 Feetech 시리얼 통신 재활용이 지름길), 이는 실기 팔이 있어야 검증된다.
- RViz 인터랙션은 디스플레이가 필요해 이 검증은 헤드리스 범위(서비스·컨트롤러 기동)까지다.
- Setup Assistant GUI 대신 파일 직접 작성이라 self-collision matrix는 인접쌍 기준의 최소 구성이다.

## Future Work

Feetech STS3215용 ros2_control 인터페이스를 붙여 실제 팔(팔로워 또는 토크를 켠 리더)에서
MoveIt 궤적 실행 → 실기 pick-and-place. 하드웨어 접근이 2026-09-08 에 끝나므로 그 전 시도 대상.

## 코드
`code/moveit-so101/` — config(URDF.xacro·SRDF·kinematics·controllers) + 표준 런치 7종.
메시(STL)는 용량상 제외(폴더 README 참조).

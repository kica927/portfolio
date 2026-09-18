# so101-gazebo-control

SO-101 팔을 Gazebo Harmonic 물리 시뮬레이션에 올려 위치 제어 → 토크 PD/PID → Pinocchio 중력 보상까지
단계별로 측정한 코드와 실행 로그다. 설명과 결과는 [`projects/so101-gazebo-control.md`](../../projects/so101-gazebo-control.md) 에 있다.

## 구성

| 폴더 | 내용 |
|---|---|
| `so101_gazebo/` | launch · 월드 · 컨트롤러 설정 · 측정/분석 스크립트 (ament_cmake) |
| `so101_gravity_comp/` | JTC 뒤에 체인으로 붙는 C++ 동역학 피드포워드 컨트롤러 (ros2_control chainable + Pinocchio). `feedforward: gravity \| nle \| full` |
| `results/` | 실행별 launch 로그와 요약 출력 (원본 CSV 는 용량상 제외) |

`so101_gazebo` 는 [`code/moveit-so101`](../moveit-so101/) 의 `so101_moveit_config` URDF 를 **수정하지 않고** 읽어,
launch 안에서 mock 하드웨어 블록만 `gz_ros2_control` 블록으로 바꾸고 world 고정 관절을 붙인다.

## 환경

```
Ubuntu 24.04 · ROS 2 Jazzy · Gazebo Harmonic 8.15.0
ros-jazzy-ros-gz · ros-jazzy-gz-ros2-control 1.2.20 · ros-jazzy-pinocchio 4.1.0
Intel Core Ultra 5 225 · 헤드리스(서버 전용, 화면 없음) · 물리 스텝 1ms
```

## 빌드

```bash
cd ~/so101_ws
colcon build --packages-select so101_moveit_config so101_gazebo so101_gravity_comp
source install/setup.bash
```

## 실행

`scripts/run_sim_test.sh <모드> <프로파일> <ROS_DOMAIN_ID> [토크한계] [태그] [컨트롤러yaml] [팔 컨트롤러 목록] [hold scale]`

```bash
S=src/so101_gazebo/scripts/run_sim_test.sh
C=$PWD/src/so101_gazebo/config
$S position step 71
$S effort step 77 "" _100hz_clean
$S effort step 86 "" _B_pd  $C/controllers_effort_1k.yaml
$S effort step 87 "" _B_pid $C/controllers_effort_1k_pid.yaml
$S effort step 88 "" _B_gc  $C/controllers_effort_1k_gc.yaml gravity_compensation,arm_controller
$S effort hold_after 92 "" _s09 $C/controllers_effort_1k_gc_s09.yaml gravity_compensation,arm_controller 0.9
$S effort step 123 "" _B_ff_full $C/controllers_effort_1k_ff_full.yaml gravity_compensation,arm_controller
```

실행마다 `GZ_PARTITION` 과 `ROS_DOMAIN_ID` 를 따로 쓰므로 도메인만 다르게 주면 동시에 돌릴 수 있다.
launch 는 별도 프로세스 그룹으로 띄워 그룹 전체를 종료한다(남은 Gazebo 가 `/clock` 을 섞어 시간이 역행한 적이 있다).

## 분석 스크립트

| 스크립트 | 하는 일 |
|---|---|
| `track_test.py` | FollowJointTrajectory 로 스텝/사인/자세A 궤적 전송, 추종 오차·토크·속도 기록 |
| `hold_test.py` | 컨트롤러 전환 전후 관절 위치·토크 기록, 초기 가속도를 모델 예측과 비교 |
| `oscillation_fft.py` | 궤적 종료 후 진동 주파수와 토크 부호 교대 비율 |
| `discrete_stability.py` | 관절 하나 모델(관성+PD+ZOH)의 폐루프 극점 |
| `mimo_stability.py` | 5관절 결합 모델의 폐루프 극점 (실측 50Hz 진동을 설명한 모델) |
| `gravity_check.py` | Pinocchio 중력 토크로 PD 처짐 예측 vs Gazebo 실측 |
| `pick_test_pose.py` · `contact_check.py` · `floor_and_onset.py` | 바닥 접촉 없는 테스트 자세 선정 · 실행 궤적 사후 접촉 검사 |
| `kick_predict.py` | 전환 순간 1ms 토크 누락이 만드는 관절 속도 예측 vs 실측 |
| `run_feedforward_matrix.sh` | 피드포워드 모드 gravity · nle · full 을 같은 궤적으로 비교 |
| `run_moveit_compare.sh` | `launch/move_group_sim.launch.py` 로 MoveIt 을 띄워 계획 궤적을 PD / computed torque 체인으로 실행 |
| `csv_coverage.py` | 기록 CSV 의 시간 범위 · 빈 구간 · 목표 궤적 범위 확인 (기록 누락 검사) |

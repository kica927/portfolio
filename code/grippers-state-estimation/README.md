# grippers-state-estimation

grippers 실기 bag 두 개(2026-09-05)로 오도메트리 · IMU · LiDAR 를 다시 분석한 코드와 결과다.
설명은 [`projects/grippers-state-estimation.md`](../../projects/grippers-state-estimation.md) 에 있다.

## 환경

```
Ubuntu 24.04 · ROS 2 Jazzy (녹화는 Humble)
ros-jazzy-robot-localization · ros-jazzy-slam-toolbox 2.8.5 · ros-jazzy-nav2-map-server
Python: numpy · scipy · rosbag2_py
```

bag 은 `bags/<이름>/` 에 두고 처음 한 번 `ros2 bag reindex bags/<이름> -s sqlite3` 로 metadata 를 만든다
(녹화본에 metadata.yaml 이 없었다).

## 보고서 (`reports/`)

`scripts/make_reports.sh` 가 전부 다시 만든다.

| 번호 | 내용 |
|---|---|
| 01 | 토픽 · 프레임 · 센서 특성 조사 |
| 02 | `/odom_raw` 가 명령 적분인지 판별 |
| 03 | `/odom_raw` 공분산의 속도 상태별 값 |
| 04 · 05 | IMU 정지 노이즈 · 회전 동역학 식별과 교차검증 |
| 06 | 고정 거리 패턴 피팅 — **기각된 분석**(자기 몸체를 바닥으로 오인) |
| 07 · 08 | 자작 ICP LiDAR 오도메트리 · 회전 과소추정 원인 조건 비교 |
| 09 | EKF 구성별 누적 · 순회전 vs IMU 적분 |
| 10 | SLAM 기준 궤적의 사전 추정값 · 임계값 민감도 |
| 11 | 기준 2종으로 명령 · EKF A~D · IMU 평가 |
| 12 | 조향 시뮬레이터 bag 검증 + 첫 비교(**최대 명령이 달라 불공정** — 기록용) |
| 13 | 최대 명령을 맞춘 조향 제어기 비교 (bang-bang · 비례 · MPC) |
| 14 | 데드밴드 크기별 조향 제어기 비교 |

## 실행

```bash
IMU_BIAS=0.00376 scripts/run_ekf.sh bags/run_20260905_150105 D_imu_bc 111
scripts/run_slam2.sh bags/run_20260905_150105 cmd 0 101
scripts/run_slam2.sh bags/run_20260905_150105 ekfB 0 102
python3 scripts/eval_trajectories.py --slam results/slam_run_20260905_150105_cmd_mt0_traj.csv \
  --ekf D_imu_bc=results/ekf_run_20260905_150105_D_imu_bc.csv --bag bags/run_20260905_150105 --imu-bias 0.00376
```

- EKF 구성: `A_cmd` · `B_cmdv_imuw` · `C_all` · `D_imu_bc` (`run_ekf.sh` 안의 case 참고)
- `run_slam.sh` 는 기본 이동 임계값 · 명령 사전 추정만 쓰는 첫 버전이고, 평가에 쓴 기준은 `run_slam2.sh` 로 만들었다.
- `slam_toolbox` 는 lifecycle 노드라 스크립트가 `configure → activate` 를 직접 보낸다.
- 스캔 점 개수가 스캔마다 달라 `scan_resampler.py` 로 1° 간격 360 점으로 고정한 뒤 넣는다.
- `imu_bias_correct.py` 는 정지 구간에서 잰 자이로 z 바이어스를 빼서 `/imu_corrected` 로 다시 발행한다.

`maps/` 의 bag 1 · 명령 사전 추정 지도는 저장 단계에서 실패해 없다(궤적은 정상 기록).

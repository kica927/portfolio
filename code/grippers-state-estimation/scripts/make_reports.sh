#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
cd ~/state-estimation
mkdir -p reports
F="grep -v Opened.database"
B1=run_20260905_150105
B2=run_20260905_151233
for B in $B1 $B2; do
  python3 scripts/inspect_bag.py bags/$B 2>&1 | $F > reports/01_inspect_$B.txt
  python3 scripts/odom_source.py bags/$B 2>&1 | $F > reports/02_odom_source_$B.txt
  python3 scripts/odom_cov_states.py bags/$B 2>&1 | $F > reports/03_odom_cov_$B.txt
done
python3 scripts/gyro_segments.py bags/$B1 bags/$B2 2>&1 | $F > reports/04_gyro_segments.txt
python3 scripts/sysid_yaw.py bags/$B1 bags/$B2 2>&1 | $F > reports/05_sysid_yaw.txt
python3 scripts/lidar_tilt.py bags/$B1 bags/$B2 2>&1 | $F > reports/06_lidar_fixed_pattern_REJECTED_fit.txt
cp results/lo_150105.txt reports/07_lidar_icp_odometry_$B1.txt
cp results/lo_151233.txt reports/07_lidar_icp_odometry_$B2.txt
python3 scripts/icp_mask_test.py bags/$B1 2>&1 | $F > reports/08_icp_bias_conditions.txt
for B in $B1 $B2; do
  if [ $B = $B1 ]; then BIAS=0.00376; else BIAS=0.00393; fi
  python3 scripts/ekf_yaw_loss.py bags/$B $BIAS results/ekf_${B}_A_cmd.csv results/ekf_${B}_B_cmdv_imuw.csv results/ekf_${B}_C_all.csv results/ekf_${B}_D_imu_bc.csv 2>&1 | $F > reports/09_ekf_yaw_loss_$B.txt
  python3 scripts/compare_refs.py results/slam_${B}_cmd_mt0_traj.csv "ekfB_prior_mt0=results/slam_${B}_ekfB_mt0_traj.csv" "cmd_prior_default_threshold=results/slam_${B}_full_lidar90_traj.csv" > reports/10_slam_reference_sensitivity_$B.txt 2>&1
  EK="A_cmd=results/ekf_${B}_A_cmd.csv B_imu_raw=results/ekf_${B}_B_cmdv_imuw.csv C_all=results/ekf_${B}_C_all.csv D_imu_bc=results/ekf_${B}_D_imu_bc.csv"
  python3 scripts/eval_trajectories.py --slam results/slam_${B}_cmd_mt0_traj.csv --odom-label "명령 오도메트리(/odom_raw)" --ekf $EK --bag bags/$B --imu-bias $BIAS 2>&1 | $F > reports/11_eval_ref_cmd_mt0_$B.txt
  python3 scripts/eval_trajectories.py --slam results/slam_${B}_ekfB_mt0_traj.csv --odom-label "기준 실행의 사전추정(=EKF B)" --ekf $EK --bag bags/$B --imu-bias $BIAS 2>&1 | $F > reports/11_eval_ref_ekfB_mt0_$B.txt
done
ls -la reports

#!/usr/bin/env bash
# run_slam.sh 확장판: SLAM 의 사전 추정(odom TF) 출처와 이동 임계값을 바꿔 기준 궤적의 사전 추정 의존성을 본다.
#   ODOM_SRC=cmd  : /odom_raw(명령 적분)를 odom TF 로 발행
#   ODOM_SRC=ekfB : EKF 구성 B(명령 병진속도 + IMU 회전속도)를 실시간으로 돌려 odom TF 로 발행
#   MIN_TRAVEL=0  : 모든 스캔을 스캔매칭에 사용 (기본 설정은 2cm / 0.05rad 미만 이동 스캔을 건너뛴다)
BAG=$1
ODOM_SRC=$2
MIN_TRAVEL=$3
DOMAIN=$4
DUR=${5:-0}
LIDAR_YAW=${6:--1.5707963}
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$DOMAIN
cd ~/state-estimation
mkdir -p results/configs results/maps
TAG=${ODOM_SRC}_mt${MIN_TRAVEL}
NAME=$(basename "$BAG")_${TAG}
CFG=results/configs/slam_${TAG}.yaml
cp /opt/ros/jazzy/share/slam_toolbox/config/mapper_params_online_sync.yaml "$CFG"
if [ "$MIN_TRAVEL" = "0" ]; then DIST=0.0; HEAD=0.0; else DIST=0.02; HEAD=0.05; fi
sed -i -E \
  -e "s#^( *)scan_topic:.*#\1scan_topic: /scan_fixed#" \
  -e "s#^( *)base_frame:.*#\1base_frame: base_footprint#" \
  -e "s#^( *)resolution:.*#\1resolution: 0.02#" \
  -e "s#^( *)max_laser_range:.*#\1max_laser_range: 6.0#" \
  -e "s#^( *)min_laser_range:.*#\1min_laser_range: 0.15#" \
  -e "s#^( *)minimum_travel_distance:.*#\1minimum_travel_distance: ${DIST}#" \
  -e "s#^( *)minimum_travel_heading:.*#\1minimum_travel_heading: ${HEAD}#" \
  -e "s#^( *)map_update_interval:.*#\1map_update_interval: 2.0#" \
  -e "s#^( *)mode:.*#\1mode: mapping#" \
  "$CFG"
grep -q "use_sim_time" "$CFG" || sed -i "s#^\( *\)ros__parameters:#\1ros__parameters:\n\1  use_sim_time: true#" "$CFG"

LIB=/opt/ros/jazzy/lib
PIDS=()
$LIB/tf2_ros/static_transform_publisher --z 0.07 --frame-id base_footprint --child-frame-id base_link >/dev/null 2>&1 & PIDS+=($!)
$LIB/tf2_ros/static_transform_publisher --x -0.0122 --z 0.0925 --yaw "$LIDAR_YAW" --frame-id base_link --child-frame-id lidar_frame >/dev/null 2>&1 & PIDS+=($!)
python3 scripts/scan_resampler.py --ros-args -p use_sim_time:=true > "results/slam_${NAME}_resampler.log" 2>&1 & PIDS+=($!)
TOPICS=(/scan_raw /odom_raw)
if [ "$ODOM_SRC" = "ekfB" ]; then
  $LIB/tf2_ros/static_transform_publisher --yaw -1.569924 --frame-id base_link --child-frame-id imu_link >/dev/null 2>&1 & PIDS+=($!)
  ECFG=results/configs/ekf_B_tf.yaml
  sed -e "s/publish_tf: false/publish_tf: true/" results/configs/ekf_B_cmdv_imuw.yaml > "$ECFG"
  $LIB/robot_localization/ekf_node --ros-args --params-file "$ECFG" -r __node:=ekf_filter_node -r odometry/filtered:=/ekf/odom > "results/slam_${NAME}_ekf.log" 2>&1 & PIDS+=($!)
  TOPICS+=(/ros_robot_controller/imu_raw)
else
  python3 scripts/odom_to_tf.py > "results/slam_${NAME}_odomtf.log" 2>&1 & PIDS+=($!)
fi
$LIB/slam_toolbox/sync_slam_toolbox_node --ros-args --params-file "$CFG" -r __node:=slam_toolbox > "results/slam_${NAME}.log" 2>&1 & PIDS+=($!)
python3 scripts/tf_logger.py "results/slam_${NAME}_traj.csv" & PIDS+=($!)
sleep 4
for T in configure activate; do
  for i in $(seq 10); do
    if timeout 10 ros2 lifecycle set /slam_toolbox $T 2>&1 | grep -q -i "successful"; then break; fi
    sleep 1
  done
done
echo "-- [$NAME] slam_toolbox 상태: $(timeout 10 ros2 lifecycle get /slam_toolbox 2>&1)"

EXTRA=()
[ "$DUR" != "0" ] && EXTRA=(--playback-duration "$DUR")
ros2 bag play "$BAG" --clock 100 --rate 0.5 "${EXTRA[@]}" --topics "${TOPICS[@]}" > "results/slam_${NAME}_play.log" 2>&1
sleep 4
timeout 30 ros2 run nav2_map_server map_saver_cli -f "results/maps/${NAME}" --ros-args -p use_sim_time:=true -p map_subscribe_transient_local:=true > "results/slam_${NAME}_mapsaver.log" 2>&1
kill -INT "${PIDS[@]}" 2>/dev/null
sleep 3
kill "${PIDS[@]}" 2>/dev/null
echo "-- [$NAME] 궤적 $(( $(wc -l < "results/slam_${NAME}_traj.csv") - 1 ))행 · 드롭 $(grep -c "dropping message" "results/slam_${NAME}.log") · 맵 $(grep -c "saved successfully" "results/slam_${NAME}_mapsaver.log")"

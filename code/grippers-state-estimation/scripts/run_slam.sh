#!/usr/bin/env bash
BAG=$1
TAG=$2
DOMAIN=$3
DUR=${4:-0}
LIDAR_YAW=${5:--1.5707963}
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$DOMAIN
cd ~/state-estimation
mkdir -p results/configs results/maps
NAME=$(basename "$BAG")_${TAG}
CFG=results/configs/slam_${TAG}.yaml
cp /opt/ros/jazzy/share/slam_toolbox/config/mapper_params_online_sync.yaml "$CFG"
sed -i -E \
  -e "s#^( *)scan_topic:.*#\1scan_topic: /scan_fixed#" \
  -e "s#^( *)base_frame:.*#\1base_frame: base_footprint#" \
  -e "s#^( *)resolution:.*#\1resolution: 0.02#" \
  -e "s#^( *)max_laser_range:.*#\1max_laser_range: 6.0#" \
  -e "s#^( *)minimum_travel_distance:.*#\1minimum_travel_distance: 0.02#" \
  -e "s#^( *)minimum_travel_heading:.*#\1minimum_travel_heading: 0.05#" \
  -e "s#^( *)map_update_interval:.*#\1map_update_interval: 2.0#" \
  -e "s#^( *)mode:.*#\1mode: mapping#" \
  "$CFG"
grep -q "use_sim_time" "$CFG" || sed -i "s#^\( *\)ros__parameters:#\1ros__parameters:\n\1  use_sim_time: true#" "$CFG"
grep -q "min_laser_range" "$CFG" || sed -i "s#^\( *\)max_laser_range:.*#&\n\1min_laser_range: 0.15#" "$CFG"

LIB=/opt/ros/jazzy/lib
PIDS=()
$LIB/tf2_ros/static_transform_publisher --z 0.07 --frame-id base_footprint --child-frame-id base_link >/dev/null 2>&1 & PIDS+=($!)
$LIB/tf2_ros/static_transform_publisher --x -0.0122 --z 0.0925 --yaw "$LIDAR_YAW" --frame-id base_link --child-frame-id lidar_frame >/dev/null 2>&1 & PIDS+=($!)
python3 scripts/scan_resampler.py --ros-args -p use_sim_time:=true > "results/slam_${NAME}_resampler.log" 2>&1 & PIDS+=($!)
python3 scripts/odom_to_tf.py > "results/slam_${NAME}_odomtf.log" 2>&1 & PIDS+=($!)
$LIB/slam_toolbox/sync_slam_toolbox_node --ros-args --params-file "$CFG" -r __node:=slam_toolbox > "results/slam_${NAME}.log" 2>&1 & PIDS+=($!)
python3 scripts/tf_logger.py "results/slam_${NAME}_traj.csv" & PIDS+=($!)
sleep 4
for T in configure activate; do
  for i in $(seq 10); do
    if timeout 10 ros2 lifecycle set /slam_toolbox $T 2>&1 | tee -a "results/slam_${NAME}_lifecycle.log" | grep -q -i "successful"; then break; fi
    sleep 1
  done
done
echo "-- slam_toolbox lifecycle 상태: $(timeout 10 ros2 lifecycle get /slam_toolbox 2>&1)"
sleep 1

EXTRA=()
[ "$DUR" != "0" ] && EXTRA=(--playback-duration "$DUR")
ros2 bag play "$BAG" --clock 100 --rate 0.5 "${EXTRA[@]}" --topics /scan_raw /odom_raw > "results/slam_${NAME}_play.log" 2>&1
sleep 4
timeout 30 ros2 run nav2_map_server map_saver_cli -f "results/maps/${NAME}" --ros-args -p use_sim_time:=true -p map_subscribe_transient_local:=true > "results/slam_${NAME}_mapsaver.log" 2>&1
kill -INT "${PIDS[@]}" 2>/dev/null
sleep 3
kill "${PIDS[@]}" 2>/dev/null
echo "궤적: results/slam_${NAME}_traj.csv $(( $(wc -l < "results/slam_${NAME}_traj.csv") - 1 ))행"
ls -la results/maps/${NAME}.* 2>/dev/null
echo "-- slam_toolbox 로그 경고/오류 (종류별)"
grep -i -E "warn|error|reject|expected|fail" "results/slam_${NAME}.log" | sed -E 's/\[[0-9]+\.[0-9]+\]//' | sort | uniq -c | sort -rn | head -n 10
echo "-- 맵 저장 로그"
tail -n 3 "results/slam_${NAME}_mapsaver.log"

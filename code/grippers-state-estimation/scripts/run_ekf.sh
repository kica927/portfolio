#!/usr/bin/env bash
BAG=$1
CONF=$2
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=$3
DUR=${4:-0}
IMU_BIAS=${IMU_BIAS:-0.0}
cd ~/state-estimation
mkdir -p results/configs
NAME=$(basename "$BAG")
OUT=results/ekf_${NAME}_${CONF}.csv
CFG=results/configs/ekf_${CONF}.yaml
LOG=results/ekf_${NAME}_${CONF}.log

V_ONLY="[false,false,false, false,false,false, true,true,false, false,false,false, false,false,false]"
V_W="[false,false,false, false,false,false, true,true,false, false,false,true, false,false,false]"
W_ONLY="[false,false,false, false,false,false, false,false,false, false,false,true, false,false,false]"
IMU_TOPIC=/ros_robot_controller/imu_raw
case $CONF in
  A_cmd) ODOM=$V_W; IMU="" ;;
  B_cmdv_imuw) ODOM=$V_ONLY; IMU=$W_ONLY ;;
  C_all) ODOM=$V_W; IMU=$W_ONLY ;;
  D_imu_bc) ODOM=$V_ONLY; IMU=$W_ONLY; IMU_TOPIC=/imu_corrected ;;
  *) echo "알 수 없는 구성: $CONF"; exit 1 ;;
esac

cat > "$CFG" <<EOF
ekf_filter_node:
  ros__parameters:
    use_sim_time: true
    frequency: 50.0
    two_d_mode: true
    publish_tf: false
    odom_frame: odom
    base_link_frame: base_footprint
    world_frame: odom
    odom0: /odom_raw
    odom0_config: $ODOM
EOF
if [ -n "$IMU" ]; then
cat >> "$CFG" <<EOF
    imu0: $IMU_TOPIC
    imu0_config: $IMU
EOF
fi

LIB=/opt/ros/jazzy/lib
PIDS=()
$LIB/tf2_ros/static_transform_publisher --z 0.07 --frame-id base_footprint --child-frame-id base_link >/dev/null 2>&1 & PIDS+=($!)
$LIB/tf2_ros/static_transform_publisher --yaw -1.569924 --frame-id base_link --child-frame-id imu_link >/dev/null 2>&1 & PIDS+=($!)
if [ "$IMU_TOPIC" = "/imu_corrected" ]; then
  python3 scripts/imu_bias_correct.py --ros-args -p bias_z:=$IMU_BIAS -p use_sim_time:=true > "results/ekf_${NAME}_${CONF}_bias.log" 2>&1 & PIDS+=($!)
fi
$LIB/robot_localization/ekf_node --ros-args --params-file "$CFG" -r __node:=ekf_filter_node -r odometry/filtered:=/ekf/odom > "$LOG" 2>&1 & PIDS+=($!)
python3 scripts/ekf_logger.py "$OUT" & PIDS+=($!)
sleep 4

EXTRA=()
[ "$DUR" != "0" ] && EXTRA=(--playback-duration "$DUR")
ros2 bag play "$BAG" --clock 100 --rate ${RATE:-2} "${EXTRA[@]}" --topics /odom_raw /ros_robot_controller/imu_raw > "results/play_${NAME}_${CONF}.log" 2>&1
sleep 3
kill -INT "${PIDS[@]}" 2>/dev/null
sleep 2
kill "${PIDS[@]}" 2>/dev/null
echo "$OUT : $(( $(wc -l < "$OUT") - 1 ))행"
echo "-- EKF 로그 경고/오류 (종류별 개수)"
grep -i -E "warn|error" "$LOG" | sed -E 's/\[[0-9.]+\]//' | sort | uniq -c | head -n 8
[ -f "results/ekf_${NAME}_${CONF}_bias.log" ] && tail -n 1 "results/ekf_${NAME}_${CONF}_bias.log"

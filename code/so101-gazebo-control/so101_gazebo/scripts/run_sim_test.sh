#!/usr/bin/env bash
MODE=$1
PROFILE=$2
DOMAIN=$3
EFFORT_LIMIT=${4:-}
TAG=${5:-}
CONTROLLERS=${6:-}
ARM_CONTROLLERS=${7:-arm_controller}
HOLD_SCALE=${8:-1.0}
LAST_ARM=${ARM_CONTROLLERS##*,}
source /opt/ros/jazzy/setup.bash
source ~/so101_ws/install/setup.bash
export ROS_DOMAIN_ID=$DOMAIN
export GZ_PARTITION=so101_$DOMAIN
mkdir -p ~/so101_ws/results
NAME=${MODE}_${PROFILE}${TAG}
LOG=~/so101_ws/results/${NAME}.launch.log

kill_same_partition() {
  for p in $(pgrep -f "gz sim -s -r"); do
    if { tr "\0" "\n" < /proc/$p/environ; } 2>/dev/null | grep -qx "GZ_PARTITION=$GZ_PARTITION"; then
      echo "== 같은 파티션($GZ_PARTITION)의 남은 Gazebo 종료: pid $p"
      kill -KILL $p
    fi
  done
}
kill_same_partition

ARGS=(control_mode:=$MODE)
[ -n "$EFFORT_LIMIT" ] && ARGS+=(effort_limit:=$EFFORT_LIMIT)
[ -n "$CONTROLLERS" ] && ARGS+=(controllers:=$CONTROLLERS)
ARGS+=(arm_controllers:=$ARM_CONTROLLERS)
setsid ros2 launch so101_gazebo sim.launch.py "${ARGS[@]}" > "$LOG" 2>&1 &
LPID=$!

READY=0
for i in $(seq 60); do
  if ! kill -0 $LPID 2>/dev/null; then echo "== [$NAME] launch 가 먼저 종료됨"; break; fi
  if timeout 10 ros2 control list_controllers 2>/dev/null | grep -E "^$LAST_ARM " | grep -q " active"; then READY=1; break; fi
  sleep 2
done
echo "== [$NAME] 컨트롤러 준비: $READY"
timeout 10 ros2 control list_controllers 2>&1 | grep -v "waiting for service" | sed 's/\x1b\[[0-9;]*m//g'
if [ "$READY" = "1" ]; then
  sleep 2
  if [ "$PROFILE" = "hold" ]; then
    timeout 300 ros2 run so101_gazebo hold_test.py --seconds 5
  elif [ "$PROFILE" = "moveit" ]; then
    MLOG=~/so101_ws/results/${NAME}.move_group.log
    setsid ros2 launch so101_gazebo move_group_sim.launch.py > "$MLOG" 2>&1 &
    MPID=$!
    for i in $(seq 60); do grep -q "You can start planning now" "$MLOG" && break; sleep 2; done
    echo "-- move_group 준비: $(grep -c 'You can start planning now' "$MLOG")"
    timeout 400 ros2 run so101_gazebo track_test.py --profile moveit --out ~/so101_ws/results/${NAME}.csv
    kill -INT -- -$MPID 2>/dev/null
    sleep 4
    kill -KILL -- -$MPID 2>/dev/null
    echo "-- move_group 로그 경고/오류"
    grep -i -E "error|warn" "$MLOG" | sed 's/\x1b\[[0-9;]*m//g' | sed -E 's/\[[0-9]+\.[0-9]+\]//' | sort | uniq -c | sort -rn | head -n 8
  elif [ "$PROFILE" = "hold_after" ]; then
    timeout 300 ros2 run so101_gazebo track_test.py --profile toA --out ~/so101_ws/results/${NAME}_toA.csv
    timeout 300 ros2 run so101_gazebo hold_test.py --seconds 3 --switch-topic /arm_controller/controller_state --scale "$HOLD_SCALE" --out ~/so101_ws/results/${NAME}_hold.csv > ~/so101_ws/results/${NAME}_hold.txt 2>&1 &
    HPID=$!
    sleep 5
    echo "-- arm_controller 비활성화 → 중력 보상 단독 (기록은 전환 전부터)"
    timeout 30 ros2 control switch_controllers --deactivate arm_controller --strict 2>&1 | grep -v "waiting for service"
    wait $HPID
    cat ~/so101_ws/results/${NAME}_hold.txt
  else
    timeout 300 ros2 run so101_gazebo track_test.py --profile "$PROFILE" --out ~/so101_ws/results/${NAME}.csv
  fi
fi

kill -INT -- -$LPID 2>/dev/null
for i in $(seq 10); do
  pgrep -g $LPID >/dev/null || break
  sleep 1
done
if pgrep -g $LPID >/dev/null; then
  echo "== [$NAME] 종료되지 않은 프로세스 강제 종료"
  kill -KILL -- -$LPID 2>/dev/null
fi
kill_same_partition
echo "== [$NAME] launch 로그의 경고/오류"
grep -i -E "error|warn|fail|malformed|backwards" "$LOG" | sed 's/\x1b\[[0-9;]*m//g' | sed -E 's/\[[0-9]+\.[0-9]+\]//' | sort | uniq -c | sort -rn | head -n 15

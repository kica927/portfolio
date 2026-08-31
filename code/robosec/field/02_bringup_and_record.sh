#!/usr/bin/env bash
# 02 — Pi 를 "주입 받을 준비" 상태로 올리고 녹화 시작 (맥에서 실행, SSH).
#
#   bash field/02_bringup_and_record.sh
#
# 노드를 띄우지만 로봇은 움직이지 않는다 — 명령이 오기 전엔 IDLE 정지 상태.
# 실제 바퀴가 도는 것은 03(사람 주입)에서만.
#
# 순서: 컨트롤러(STM32) → orchestrator(5005 수신) → 녹화 → 검증.
set -u
PI="${PI:-pi@192.0.2.7}"
# orchestrator 가 보고(5006)를 보낼 맥 IP (baseline 은 이 주소로만 보고).
MAC_IP="${MAC_IP:-$(ipconfig getifaddr en0 2>/dev/null || echo 192.0.2.10)}"

SRC='export ROS_DOMAIN_ID=21; export need_compile=False; export DEPTH_CAMERA_TYPE=ascamera; export MACHINE_TYPE=MentorPi_Mecanum; source /opt/ros/humble/setup.bash; source /ros2_ws/install/setup.bash; source /home/ubuntu/third_party_ros2/third_party_ws/install/setup.bash'

echo ">> 맥 IP (orchestrator host_ip) = $MAC_IP"
echo

echo "==================== 1) 모터 컨트롤러 (STM32) — 먼저 ===================="
ssh "$PI" "docker exec -d IntelPi bash -lc '$SRC; nohup ros2 launch controller odom_publisher.launch.py > /shared/robosec_ctrl.log 2>&1 &'"
echo ">> 컨트롤러 기동 요청 → /shared/robosec_ctrl.log · STM32 재초기화까지 6초 대기"
sleep 6

echo
echo "==================== 2) orchestrator (5005 수신, 팔=fake, 바퀴=진짜) ===================="
ssh "$PI" "docker exec -d IntelPi bash -lc '$SRC; nohup ros2 run grippers_mission mission_orchestrator --ros-args -p use_fake_host:=false -p use_fake_arm:=true -p use_fake_base:=false -p host_ip:=$MAC_IP > /shared/robosec_orch.log 2>&1 &'"
echo ">> orchestrator 기동 요청 → /shared/robosec_orch.log · 5초 대기"
sleep 5

echo
echo "==================== 3) 녹화 시작 (pi_capture, 구독만) ===================="
ssh "$PI" "docker exec IntelPi bash -lc 'ls /tmp/pi_capture/tap.py >/dev/null 2>&1'" \
  || { echo ">> pi_capture 미배포 → deploy 먼저"; ( cd ~/Desktop/intel/pi_capture && ./deploy.sh ); }
ssh "$PI" "docker exec -d IntelPi bash -lc '$SRC; nohup python3 /tmp/pi_capture/tap.py --out /shared/capture_out/robosec1 --topics /cmd_vel /mission/state --label \"robosec 확증\" > /shared/robosec_tap.log 2>&1 &'"
echo ">> 녹화 시작 → /shared/capture_out/robosec1 (호스트 마운트라 전원 끊겨도 살아남음)"
echo "   로그 /shared/robosec_tap.log · 3초 대기"
sleep 3

echo
echo "==================== 4) 검증 — 이게 통과해야 03 로 간다 ===================="
echo "--- /cmd_vel 구독자 (컨트롤러 붙었나, 1 이상이어야) ---"
ssh "$PI" "docker exec IntelPi bash -lc '$SRC; ros2 topic info /cmd_vel'" 2>&1 | grep -i "Subscription count" || echo "  (조회 실패)"
echo "--- /mission_orchestrator 노드 (5005 열렸나) ---"
ssh "$PI" "docker exec IntelPi bash -lc '$SRC; ros2 node list'" 2>&1 | grep -E "mission_orchestrator" || echo "  !! orchestrator 안 보임"
echo "--- 현재 상태 (IDLE 이어야) ---"
ssh "$PI" "docker exec IntelPi bash -lc '$SRC; timeout 5 ros2 topic echo /mission/state --once'" 2>&1 | grep -iE "IDLE|data" | head -3
echo "--- 녹화 살아있나 ---"
ssh "$PI" "docker exec IntelPi bash -lc 'ls -la /shared/capture_out/robosec1 2>/dev/null'" 2>&1 | head

echo
echo "✅ 검증 위 세 줄 확인:  구독자 ≥ 1  ·  /mission_orchestrator 보임  ·  상태 IDLE"
echo "   모두 맞으면 → 사람이 03(주입)을 진행. 하나라도 아니면 여기서 멈추고 로그 확인."

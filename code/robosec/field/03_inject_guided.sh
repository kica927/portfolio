#!/usr/bin/env bash
# 03 — 공격 주입 (사람이 실행하는 유일한 단계). 실제 바퀴가 움직인다.
#
#   bash field/03_inject_guided.sh
#
# ⚠️ 반드시 사람이:
#   - 차량을 받침대에 올려 바퀴를 띄우고 (병진·충돌 차단 — 1차 안전장치)
#   - 만일에 대비해 메인 전원 스위치를 손 닿는 곳에 (최후수단 — Pi 도 같이 꺼짐)
#   - 각 공격 전 Enter 를 눌러 하나씩 진행한다 (자동 연발 아님)
#
# 순서는 a1 → a5(F2) → a4(F1) → a2 → a3. a5 를 a4 보다 먼저(a4 가 IDLE→APPROACH
# 로 옮기므로). a5 직전에 IDLE 을 확인한다.
set -u
PI_IP="${PI_IP:-192.0.2.7}"
PI="${PI:-pi@192.0.2.7}"
ROBOSEC="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-$HOME/Desktop/intel/.venv_test/bin/python}"; [ -x "$PY" ] || PY=python3
cd "$ROBOSEC"

step() {  # $1=제목  $2=관찰포인트  $3...=명령
  local title="$1" watch="$2"; shift 2
  echo
  echo "──────────────────────────────────────────────────────────────"
  echo "  $title"
  echo "  관찰: $watch"
  echo "──────────────────────────────────────────────────────────────"
  echo "  [안전] 바퀴 띄웠나? 전원 스위치 손 닿는 곳? 확인되면 Enter (건너뛰려면 s+Enter)"
  read -r ans
  [ "$ans" = "s" ] && { echo "  → 건너뜀"; return; }
  echo "  ▶ $*"
  "$@"
  echo "  ⏱  다음까지 30초 — 그 사이 차량이 알려진 IDLE 상태로 돌아왔는지 확인"
  sleep 30
}

echo "PI_IP=$PI_IP · attacker=$PY attacker.py"
echo "바퀴는 띄워 둔다. 각 단계는 Enter 로 진행. 정말 이상하면 => 메인 전원(최후수단, Pi 도 꺼짐)."

step "1/5  a1-corruption (D5)" \
     "바퀴가 움직이면 안 된다 — 손상 패킷은 버려져야" \
     "$PY" attacker.py a1-corruption --target "$PI_IP" --live

echo
echo "== a5 전 IDLE 확인 =="
ssh "$PI" "docker exec IntelPi bash -lc 'export ROS_DOMAIN_ID=21; source /opt/ros/humble/setup.bash; source /ros2_ws/install/setup.bash; timeout 5 ros2 topic echo /mission/state --once'" 2>&1 | grep -iE "IDLE|data" | head -2
echo "위가 IDLE 이 아니면 a5 는 F2 를 시험하지 못한다 — 정상 IDLE 로 복귀 후 진행."

step "2/5  a5-state-mismatch (F2)" \
     "IDLE 인데 바퀴가 도는가 — 돌면 F2 확증" \
     "$PY" attacker.py a5-state-mismatch --target "$PI_IP" --live

step "3/5  a4-extreme (F1)" \
     "다섯째(마지막) 패킷이 nan. 정지/유지/폭주 중 무엇인지 눈+녹화로 기록" \
     "$PY" attacker.py a4-extreme --target "$PI_IP" --state APPROACH --live

step "4/5  a2-spin-impurity (D2)" \
     "회전+병진 혼합 → 거부되고 차가 서야" \
     "$PY" attacker.py a2-spin-impurity --target "$PI_IP" --live

step "5/5  a3-replay (시퀀스 부재)" \
     "재전송 30회가 상태를 흔드는가" \
     "$PY" attacker.py a3-replay --target "$PI_IP" --count 30 --live

echo
echo "✅ 주입 종료. 04 로 넘어가 녹화를 회수·분석한다."
echo "   F1(a4 nan) 관찰 결과를 지금 메모: 정지 / 마지막값 유지 / 폭주 중 무엇이었나."

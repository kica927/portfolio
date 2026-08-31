#!/usr/bin/env bash
# 01 — 실기 전 점검 (맥, 하드웨어 불필요·안전). 사람 손 불필요, 제가 돌려도 됨.
#
#   bash field/01_preflight.sh
#
# 하는 일: 소프트웨어 20/21 재확인 + 공격목록 + Pi 도달성 + Pi 브랜치가 baseline 인지.
set -u
PI="${PI:-pi@192.0.2.7}"
ROBOSEC="$(cd "$(dirname "$0")/.." && pwd)"
rc=0

echo "==================== 1) 소프트웨어 테스트 (baseline 대상) ===================="
bash "$ROBOSEC/run_tests.sh" 2>&1 | grep -vE "Updating files|Preparing worktree" || rc=1

echo
echo "==================== 2) Pi 도달성 ===================="
if ssh -o ConnectTimeout=8 "$PI" 'echo OK $(hostname)'; then
  echo ">> Pi 도달 OK"
else
  echo ">> !! Pi 에 못 붙음 ($PI) — 전원/네트워크 확인"; rc=1
fi

echo
echo "==================== 3) Pi 배포 브랜치가 baseline 인가 ===================="
head=$(ssh -o ConnectTimeout=8 "$PI" "docker exec IntelPi bash -lc 'cd /grippers && git branch --show-current && git rev-parse --short HEAD'" 2>/dev/null)
echo "$head"
echo "$head" | grep -q "baseline_mission" \
  && echo ">> OK — baseline_mission 체크아웃" \
  || { echo ">> !! baseline 이 아님 — 02 전에 baseline 으로 스왑 필요"; rc=1; }

echo
[ $rc -eq 0 ] && echo "✅ 실기 준비 OK — 02 로 진행" || echo "⚠️ 위 실패 해결 후 진행 (rc=$rc)"
exit $rc

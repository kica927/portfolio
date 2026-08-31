#!/usr/bin/env bash
# RoboSec 소프트웨어 테스트 러너 — 하드웨어 불필요.
#
# grippers baseline(= 9/8 실기에서 Pi 가 실행하는 배포본)을 대상으로:
#   1) baseline probe  — 배포본 그대로. F1(NaN 누출)·F2 는 "문서화된 발견"이므로
#                        19/21 이 정상이다(F1 관련 2건이 의도적으로 FAIL).
#   2) patched probe   — patches/F1_resolve_motion_nonfinite.patch 를 얹은 트리.
#                        F1 이 닫혀 21/21 이어야 한다. baseline 은 건드리지 않는다.
#   3) invariant 자가검증 + (있으면) 실측 bag 스캔
#   4) attacker 목록(전송 없음)
#
# baseline 워크트리를 자동 생성해 GRIPPERS_ROOT 로 물린다 — 맥 메인 클론을 안 건드린다.
#
#   bash run_tests.sh
#
set -u
ROBOSEC_DIR="$(cd "$(dirname "$0")" && pwd)"
GRIPPERS_REPO="${GRIPPERS_REPO:-$HOME/Desktop/intel/grippers}"
WT="${GRIPPERS_BASELINE_WT:-$HOME/Desktop/intel/grippers-baseline-wt}"
PT="${GRIPPERS_PATCHED_WT:-$HOME/Desktop/intel/grippers-patched-wt}"
BASELINE_REF="${BASELINE_REF:-origin/kica927/baseline_mission}"
PATCH="$ROBOSEC_DIR/patches/F1_resolve_motion_nonfinite.patch"
PY="${PY:-$HOME/Desktop/intel/.venv_test/bin/python}"
[ -x "$PY" ] || PY=python3

if [ ! -d "$WT/domain" ]; then
  echo ">> baseline 워크트리 생성: $WT"
  git -C "$GRIPPERS_REPO" worktree add --detach "$WT" "$BASELINE_REF" || exit 1
else
  git -C "$WT" checkout --detach "$BASELINE_REF" >/dev/null 2>&1 || true
fi
echo ">> GRIPPERS_ROOT(baseline) = $WT ($(git -C "$WT" rev-parse --short HEAD 2>/dev/null))"
echo ">> python                  = $PY ($($PY --version 2>&1))"
echo

cd "$ROBOSEC_DIR"
rc=0

echo "==================== 1) baseline probe (배포본 그대로 · 19/21 기대) ===================="
probe_out="$(GRIPPERS_ROOT="$WT" PYTHONPATH=. "$PY" run_probes.py 2>&1)"; echo "$probe_out"
total="$(printf '%s\n' "$probe_out" | grep -oE '전체: [0-9]+/21' | head -1)"
nfail="$(printf '%s\n' "$probe_out" | grep -c '\*\*FAIL\*\*')"
nfail_nan="$(printf '%s\n' "$probe_out" | grep '\*\*FAIL\*\*' | grep -c 'nan')"
if [ "$total" = "전체: 19/21" ] && [ "$nfail" -eq 2 ] && [ "$nfail_nan" -eq 2 ]; then
  echo ">> OK — 19/21. 두 FAIL 모두 F1(NaN 베이스 누출) = 배포본의 문서화된 발견(취약점)."
else
  echo ">> !! baseline 기대와 다름 (19/21 · F1 2건이어야 함): total='$total' fail=$nfail nan=$nfail_nan"; rc=1
fi
echo

echo "==================== 2) patched probe (F1 패치 적용 · 21/21 기대) ===================="
if [ ! -f "$PATCH" ]; then
  echo ">> !! 패치 파일 없음: $PATCH"; rc=1
else
  rm -rf "$PT" && mkdir -p "$PT" && cp -R "$WT/domain" "$PT/domain"
  if ( cd "$PT" && patch -p1 -s < "$PATCH" ); then
    patch_out="$(GRIPPERS_ROOT="$PT" PYTHONPATH=. "$PY" run_probes.py 2>&1)"
    ptotal="$(printf '%s\n' "$patch_out" | grep -oE '전체: [0-9]+/21' | head -1)"
    if [ "$ptotal" = "전체: 21/21" ]; then
      echo ">> OK — 21/21. F1 이 _clamp 비유한값 가드로 닫힘(NaN/Inf→정지)."
    else
      printf '%s\n' "$patch_out" | tail -8
      echo ">> !! patched 가 21/21 아님: '$ptotal'"; rc=1
    fi
  else
    echo ">> !! 패치 적용 실패"; rc=1
  fi
fi
echo

echo "==================== 3) invariant_check --selftest ===================="
if GRIPPERS_ROOT="$WT" "$PY" offline/invariant_check.py --selftest; then echo ">> OK"; else echo ">> !! selftest 실패"; rc=1; fi
echo

echo "==================== 3b) 실측 bag 스캔 (있으면) ===================="
for f in results/run_robosec1.jsonl results/run_robosec2.jsonl; do
  [ -f "$f" ] && { echo "--- $f ---"; GRIPPERS_ROOT="$WT" "$PY" offline/invariant_check.py "$f" 2>&1 | tail -6; }
done
echo

echo "==================== 4) attacker list (dry, 전송 없음) ===================="
if GRIPPERS_ROOT="$WT" "$PY" attacker.py list; then echo ">> OK"; else echo ">> !! attacker list 실패"; rc=1; fi
echo

echo "==================== 5) F2 before/after (보안 프레이밍이 스푸핑·재전송 차단) ===================="
f2_out="$(GRIPPERS_ROOT="$WT" PYTHONPATH=. "$PY" f2_before_after.py 2>&1)"; echo "$f2_out"
if echo "$f2_out" | grep -q "F2 닫힘"; then echo ">> OK — OLD 공격 2/2 통과, NEW 0/2 (HMAC+시퀀스)"; else echo ">> !! F2 데모 기대와 다름"; rc=1; fi
echo

if [ $rc -eq 0 ]; then
  echo "=============================================================="
  echo "✅ 소프트웨어 테스트 통과 — baseline 19/21(F1 발견) + patched 21/21(F1 닫힘)"
  echo "   + selftest + 실측 bag 스캔 + 공격목록 + F2 before/after. 실기 §3.5~§4 는 이 러너 밖이다."
else
  echo "⚠️ 실패 있음 (rc=$rc) — 위 출력 확인"
fi
exit $rc

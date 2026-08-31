#!/usr/bin/env bash
# 04 — 녹화 회수 + 오프라인 불변식 스캔 + 20/21 예측 대조 (맥, 안전). 제가 돌려도 됨.
#
#   bash field/04_collect_and_analyze.sh
set -u
PI="${PI:-pi@192.0.2.7}"
ROBOSEC="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-$HOME/Desktop/intel/.venv_test/bin/python}"; [ -x "$PY" ] || PY=python3
DEST="${DEST:-$HOME/Desktop/intel/grippers_recordings_final}"
RUN="${RUN:-robosec1}"

echo "==================== 1) 녹화 정지 ===================="
ssh "$PI" "docker exec IntelPi bash -lc 'pkill -f \"tap.py\" 2>/dev/null; echo tap 정지'" 2>&1

echo
echo "==================== 2) 맥으로 회수 (/shared 에서 직접 — 전원 끊겨도 남아있음) ===================="
mkdir -p "$DEST"
scp -q -p -r "$PI":"~/docker/shared/capture_out/$RUN" "$DEST/" \
  && echo ">> 회수 완료: $DEST/$RUN" \
  || echo ">> !! 회수 실패 — Pi 의 ~/docker/shared/capture_out/$RUN 확인"
ls -la "$DEST/$RUN" 2>/dev/null || echo ">> $DEST/$RUN 없음 — 녹화 경로 확인"

echo
echo "==================== 3) CSV → JSONL → 불변식 스캔 ===================="
cd "$ROBOSEC"
"$PY" offline/csv_to_jsonl.py "$DEST/$RUN" -o "$ROBOSEC/results/run_${RUN}.jsonl" \
  && "$PY" offline/invariant_check.py "$ROBOSEC/results/run_${RUN}.jsonl" \
  || echo ">> 토픽/컬럼 이름이 다르면 위 에러의 목록을 보고 다시"

echo
echo "==================== 4) 다음 할 일 (제가 정리) ===================="
echo "  - 위 위반 목록을 in-process 예측(20/21)과 한 줄씩 대조"
echo "  - results/onhardware_2026-09-08.md 로 정리 (어긋나는 줄 = 모델 vs 실물)"
echo "  - F1(a4 nan) 실물 관찰(정지/유지/폭주)을 그 문서에 같이 기록"

#!/bin/bash
source ~/a2venv/bin/activate
cd ~/a2_dataset/dataset
echo "===== A2-b: 합성학습 모델 → 실사 14장 평가 ====="
printf "%-9s %14s %11s\n" "fraction" "real_mAP50-95" "real_mAP50"
for F in 0.1 0.25 0.5 1.0; do
  M="$HOME/a2_runs/frac_$F/weights/best.pt"
  [ -f "$M" ] || { printf "%-9s %s\n" "$F" "모델없음(A2-a 미완)"; continue; }
  line=$(yolo detect val model="$M" data=real_test.yaml split=val imgsz=640 \
    name="real_$F" project="$HOME/a2_runs" exist_ok=true plots=False verbose=False 2>&1 \
    | awk '/^ *all /{print $(NF-1), $NF}')
  printf "%-9s %14s %11s\n" "$F" ${line:-"?  ?"}
done
echo "A2B_DONE"

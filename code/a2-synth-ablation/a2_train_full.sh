#!/bin/bash
source ~/a2venv/bin/activate
cd ~/a2_dataset/dataset
for F in 0.1 0.25 0.5 1.0; do
  echo "########## fraction=$F start $(date +%H:%M:%S) ##########"
  yolo detect train model=yolo11n.pt data=data.yaml epochs=50 imgsz=640 device=xpu \
    fraction=$F batch=16 workers=4 name=frac_$F project="$HOME/a2_runs" exist_ok=true plots=False 2>&1 | tail -4
  echo "########## fraction=$F done $(date +%H:%M:%S) ##########"
done
echo "########## SUMMARY ##########"
python - <<PY
import csv, os
print(f"{'fraction':9} {'train_imgs':>10} {'best_mAP50-95':>13} {'best_mAP50':>11}")
for F,n in [("0.1",239),("0.25",597),("0.5",1194),("1.0",2388)]:
    p=os.path.expanduser(f"~/a2_runs/frac_{F}/results.csv")
    if not os.path.exists(p): print(f"{F:9} no results"); continue
    rows=list(csv.DictReader(open(p)))
    k9=[k for k in rows[0] if "mAP50-95" in k][0]
    k5=[k for k in rows[0] if "mAP50(" in k][0]
    b=max(rows,key=lambda r: float(r[k9]))
    print(f"{F:9} {n:10} {float(b[k9]):13.4f} {float(b[k5]):11.4f}")
PY
echo A2A_FULL_DONE

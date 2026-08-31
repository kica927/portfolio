import os
from ultralytics import YOLO
data=os.path.expanduser("~/a2_dataset/dataset/real_test.yaml")
print("frac\treal_mAP50-95\treal_mAP50\tprecision\trecall")
for F in ["0.1","0.25","0.5","1.0"]:
    m=os.path.expanduser(f"~/a2_runs/frac_{F}/weights/best.pt")
    if not os.path.exists(m):
        print(F,"no model"); continue
    r=YOLO(m).val(data=data, imgsz=640, split="val", verbose=False, plots=False)
    print(f"{F}\t{r.box.map:.4f}\t{r.box.map50:.4f}\t{r.box.mp:.4f}\t{r.box.mr:.4f}")
print("A2B_PY_DONE")

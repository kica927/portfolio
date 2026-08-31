import os
from ultralytics import YOLO
D=os.path.expanduser("~/a2_dataset/dataset")
imgdir=D+"/images/test_real"
# 층화 분할: staged/distant/kakao-clean/kakao-clutter 골고루
test=["attached_2026-08-2x_7_grab_rgb2.png","attached_2026-08-23_3_rgb_snapshot3.jpg",
      "KakaoTalk_20260820_230133103_01.jpg","KakaoTalk_20260820_230133103_04.jpg",
      "attached_2026-08-2x_9_live_rgb.png"]
allf=sorted(os.listdir(imgdir))
train=[f for f in allf if f not in test]
open(D+"/real_train.txt","w").write("\n".join(imgdir+"/"+x for x in train)+"\n")
open(D+"/real_test.txt","w").write("\n".join(imgdir+"/"+x for x in test)+"\n")
yaml=f"""path: {D}
train: real_train.txt
val: real_test.txt
names:
  0: knight
  1: queen
  2: rook
  3: box
  4: soccer
  5: star
"""
open(D+"/realsplit.yaml","w").write(yaml)
print(f"split: train={len(train)} test={len(test)}")

data=D+"/realsplit.yaml"
def ev(m,tag):
    r=YOLO(m).val(data=data,imgsz=640,split="val",verbose=False,plots=False)
    print(f"{tag}: mAP50-95={r.box.map:.4f} mAP50={r.box.map50:.4f} P={r.box.mp:.4f} R={r.box.mr:.4f}")

syn=os.path.expanduser("~/a2_runs/frac_1.0/weights/best.pt")
print("=== BASELINE (합성만, frac_1.0) on real_test ===")
ev(syn,"BASELINE")

print("=== FINE-TUNE on 9 real images ===")
YOLO(syn).train(data=data, epochs=80, imgsz=640, device="xpu", batch=8, workers=4,
                lr0=0.001, patience=100, name="ft_real", project=os.path.expanduser("~/a2_runs"),
                exist_ok=True, plots=False, verbose=False)
ft=os.path.expanduser("~/a2_runs/ft_real/weights/best.pt")
print("=== FINETUNED on real_test ===")
ev(ft,"FINETUNED")
print("A2BEXT_DONE")

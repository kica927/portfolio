import os
from ultralytics import YOLO

WEIGHTS = os.path.expanduser(
    "~/portfolio_autonomous/perception/results/bdd_subset_finetune/weights/best.pt"
)
SOURCE_DIR = os.path.expanduser("~/portfolio_autonomous/carla_output/frames")
OUT_PROJECT = os.path.expanduser("~/portfolio_autonomous/carla_output")
OUT_NAME = "yolo_inference"


def main():
    model = YOLO(WEIGHTS)
    results = model.predict(
        source=SOURCE_DIR,
        device="cpu",
        imgsz=640,
        conf=0.25,
        save=True,
        project=OUT_PROJECT,
        name=OUT_NAME,
        exist_ok=True,
        max_det=100,
    )
    for r in results:
        n = 0 if r.boxes is None else len(r.boxes)
        print(os.path.basename(r.path), "-> detections:", n)


if __name__ == "__main__":
    main()

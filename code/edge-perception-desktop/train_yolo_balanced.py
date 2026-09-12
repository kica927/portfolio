import os, time, json
from ultralytics import YOLO

BASE = os.path.expanduser("~/portfolio_autonomous/perception")
DATA_YAML = os.path.join(BASE, "data", "bdd_subset_balanced", "data.yaml")
RESULTS = os.path.join(BASE, "results_balanced")
os.makedirs(RESULTS, exist_ok=True)

DEVICE = "xpu"

# epoch=40 유지: 기존(무작위 1000장) 실험과 학습 예산(epoch)을 동일하게 고정해
# "데이터 변화"만이 성능 차이의 원인이 되도록 통제한다(대신 학습 시간은 데이터가
# 3배로 늘어난 만큼 길어질 것으로 예상 — 기존 49분 -> 대략 2.5시간 내외 추정).

def main():
    t0 = time.time()
    model = YOLO("yolo11n.pt")

    pred_dir = os.path.join(RESULTS, "pretrained_preview")
    model.predict(
        source=os.path.join(BASE, "data", "bdd_subset_balanced", "images", "val"),
        device=DEVICE,
        imgsz=640,
        conf=0.25,
        save=True,
        project=RESULTS,
        name="pretrained_preview",
        exist_ok=True,
        max_det=100,
    )

    train_results = model.train(
        data=DATA_YAML,
        epochs=40,
        imgsz=640,
        batch=16,
        device=DEVICE,
        project=RESULTS,
        name="bdd_subset_balanced_finetune",
        exist_ok=True,
        patience=15,
        workers=4,
        verbose=True,
    )

    val_results = model.val(
        data=DATA_YAML,
        device=DEVICE,
        imgsz=640,
        project=RESULTS,
        name="bdd_subset_balanced_val",
        exist_ok=True,
    )

    metrics = {
        "map50-95": float(val_results.box.map),
        "map50": float(val_results.box.map50),
        "map75": float(val_results.box.map75),
        "precision_mean": float(val_results.box.mp),
        "recall_mean": float(val_results.box.mr),
        "per_class_map50": {
            name: float(val_results.box.maps[i])
            for i, name in val_results.names.items()
        } if hasattr(val_results, "names") else {},
        "elapsed_sec": time.time() - t0,
        "device": DEVICE,
        "n_train": 2400,
        "n_val": 600,
    }
    with open(os.path.join(RESULTS, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))

    best = os.path.join(RESULTS, "bdd_subset_balanced_finetune", "weights", "best.pt")
    ft_model = YOLO(best)
    ft_model.predict(
        source=os.path.join(BASE, "data", "bdd_subset_balanced", "images", "val"),
        device=DEVICE,
        imgsz=640,
        conf=0.25,
        save=True,
        project=RESULTS,
        name="finetuned_preview",
        exist_ok=True,
        max_det=100,
    )

if __name__ == "__main__":
    main()

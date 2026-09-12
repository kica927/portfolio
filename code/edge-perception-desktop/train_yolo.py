import os, time, json
from ultralytics import YOLO

BASE = os.path.expanduser("~/portfolio_autonomous/perception")
DATA_YAML = os.path.join(BASE, "data", "bdd_subset", "data.yaml")
RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)

DEVICE = "xpu"

def main():
    t0 = time.time()
    model = YOLO("yolo11n.pt")

    # 1) baseline: COCO 사전학습 가중치로 BDD 서브셋 val에 대해 추론만 수행 (파인튜닝 전)
    pred_dir = os.path.join(RESULTS, "pretrained_preview")
    model.predict(
        source=os.path.join(BASE, "data", "bdd_subset", "images", "val"),
        device=DEVICE,
        imgsz=640,
        conf=0.25,
        save=True,
        project=RESULTS,
        name="pretrained_preview",
        exist_ok=True,
        max_det=100,
    )

    # 2) BDD100K 서브셋(10 classes)으로 파인튜닝
    train_results = model.train(
        data=DATA_YAML,
        epochs=40,
        imgsz=640,
        batch=16,
        device=DEVICE,
        project=RESULTS,
        name="bdd_subset_finetune",
        exist_ok=True,
        patience=15,
        workers=4,
        verbose=True,
    )

    # 3) 검증 (mAP 등 정량 지표)
    val_results = model.val(
        data=DATA_YAML,
        device=DEVICE,
        imgsz=640,
        project=RESULTS,
        name="bdd_subset_val",
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
    }
    with open(os.path.join(RESULTS, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))

    # 4) 파인튜닝된 모델로 val 이미지 몇 장 예측 저장 (before/after 비교용)
    best = os.path.join(RESULTS, "bdd_subset_finetune", "weights", "best.pt")
    ft_model = YOLO(best)
    ft_model.predict(
        source=os.path.join(BASE, "data", "bdd_subset", "images", "val"),
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

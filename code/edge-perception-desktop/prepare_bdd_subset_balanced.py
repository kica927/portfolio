import json, random, os, sys, shutil
from concurrent.futures import ThreadPoolExecutor
import urllib.request

random.seed(42)

BASE = os.path.expanduser("~/portfolio_autonomous/perception")
SAMPLES_JSON = os.path.join(BASE, "data", "samples.json")
OLD_SUBSET = os.path.join(BASE, "data", "bdd_subset")  # 기존 무작위 1000장 (재사용 가능하면 재다운로드 생략)
OUT = os.path.join(BASE, "data", "bdd_subset_balanced")

# --- 규모 결정 근거 ---
# 원본 dgural/bdd100k는 validation split 미러 10,000장이 전부다(그 이상 없음).
# 희귀 4클래스(rider/bicycle/motorcycle/train) 중 하나라도 있는 이미지는 10,000장 중 912장(9.12%)뿐.
# 이 912장을 전부 포함하고, 나머지를 무작위로 채워 총 3,000장(기존 1,000장의 3배)으로 확장한다.
# - 전체 10,000장을 다 쓰면(약 10배) 40 epoch 학습 시간이 선형에 가깝게 늘어나(추정 8시간+)
#   포트폴리오 재실험의 시간 예산을 크게 초과한다.
# - 3,000장이면 희귀 이미지 비중이 912/3000=30.4%로, 원본 전체 비율(9.12%)의 3배 이상으로
#   오버샘플링되어 "규모 확대"와 "클래스 균형" 두 목표를 함께 달성하면서, 학습 시간은
#   기존 대비 약 3배(약 2.5시간) 수준으로 억제된다.
N_TOTAL = 3000
VAL_RATIO = 0.2

RARE_CLASSES = ["train", "motorcycle", "rider", "bicycle"]  # 희소한 순서대로 먼저 stratify

CLASS_MAP = {
    "car": 0,
    "truck": 1,
    "bus": 2,
    "pedestrian": 3,
    "rider": 4,
    "bicycle": 5,
    "motorcycle": 6,
    "traffic light": 7,
    "traffic sign": 8,
    "train": 9,
}
CLASS_NAMES = [k for k, v in sorted(CLASS_MAP.items(), key=lambda kv: kv[1])]

HF_RESOLVE = "https://huggingface.co/datasets/dgural/bdd100k/resolve/main/"


def find_existing(fname):
    """기존 bdd_subset(무작위 1000장)에 같은 파일이 이미 있으면 그 경로를 반환(재다운로드 절약)."""
    for split in ("train", "val"):
        p = os.path.join(OLD_SUBSET, "images", split, fname)
        if os.path.exists(p):
            return p
    return None


def main():
    data = json.load(open(SAMPLES_JSON))["samples"]
    print(f"전체 샘플 수: {len(data)}")

    # 이미지별 라벨 집합 계산
    image_labels = []
    for s in data:
        dets = (s.get("detections") or {}).get("detections", [])
        labels = {d["label"] for d in dets}
        image_labels.append((s, labels))

    # 'train' 클래스 자체 희소성 실측 기록
    train_imgs = [s for s, labels in image_labels if "train" in labels]
    print(f"'train' 클래스 포함 이미지: {len(train_imgs)}장 (전체 10,000장 중) "
          f"— {'데이터셋 자체의 한계(극희소)' if len(train_imgs) < 5 else '희소하지만 소수 존재'}")

    rare_by_class = {c: [s for s, labels in image_labels if c in labels] for c in RARE_CLASSES}
    for c in RARE_CLASSES:
        print(f"희귀클래스 '{c}' 포함 이미지: {len(rare_by_class[c])}장")

    rare_union_ids = set()
    for c in RARE_CLASSES:
        for s in rare_by_class[c]:
            rare_union_ids.add(id(s))
    print(f"희귀 4클래스 중 하나라도 포함하는 이미지(합집합): {len(rare_union_ids)}장")

    # --- 희귀클래스 이미지: 클래스별로 stratified train/val 배정 (희소한 클래스부터) ---
    assigned = {}  # id(sample) -> 'train' | 'val'
    id_to_sample = {}
    for c in RARE_CLASSES:
        items = [s for s in rare_by_class[c] if id(s) not in assigned]
        random.shuffle(items)
        n_val_c = max(1, round(len(items) * VAL_RATIO)) if len(items) >= 2 else 0
        for s in items[:n_val_c]:
            assigned[id(s)] = "val"
            id_to_sample[id(s)] = s
        for s in items[n_val_c:]:
            assigned[id(s)] = "train"
            id_to_sample[id(s)] = s

    rare_train = [id_to_sample[i] for i, sp in assigned.items() if sp == "train"]
    rare_val = [id_to_sample[i] for i, sp in assigned.items() if sp == "val"]
    print(f"희귀 이미지 배정: train={len(rare_train)} val={len(rare_val)}")

    # --- 나머지는 무작위로 채워 총 N_TOTAL 규모까지 확장 ---
    other_items = [s for s, labels in image_labels if id(s) not in assigned]
    random.shuffle(other_items)
    remaining_budget = max(N_TOTAL - len(assigned), 0)
    fill_items = other_items[:remaining_budget]
    random.shuffle(fill_items)
    n_val_fill = round(len(fill_items) * VAL_RATIO)
    fill_val = fill_items[:n_val_fill]
    fill_train = fill_items[n_val_fill:]
    print(f"무작위 채움: train={len(fill_train)} val={len(fill_val)} (예산={remaining_budget})")

    train_set = rare_train + fill_train
    val_set = rare_val + fill_val
    chosen = train_set + val_set
    print(f"최종 규모: train={len(train_set)} val={len(val_set)} total={len(chosen)}")

    for split in ("images/train", "images/val", "labels/train", "labels/val"):
        os.makedirs(os.path.join(OUT, split), exist_ok=True)

    val_ids = set(id(s) for s in val_set)

    def process(item):
        s = item
        filepath = s["filepath"]
        fname = os.path.basename(filepath)
        stem = os.path.splitext(fname)[0]
        split = "val" if id(s) in val_ids else "train"
        img_out = os.path.join(OUT, "images", split, fname)
        lbl_out = os.path.join(OUT, "labels", split, stem + ".txt")

        if not os.path.exists(img_out):
            existing = find_existing(fname)
            try:
                if existing:
                    shutil.copyfile(existing, img_out)
                else:
                    url = HF_RESOLVE + filepath
                    urllib.request.urlretrieve(url, img_out)
            except Exception as e:
                print("FAIL", fname, e, file=sys.stderr)
                return None

        lines = []
        dets = (s.get("detections") or {}).get("detections", [])
        for d in dets:
            label = d["label"]
            if label not in CLASS_MAP:
                continue
            cls = CLASS_MAP[label]
            x, y, w, h = d["bounding_box"]
            xc = x + w / 2
            yc = y + h / 2
            xc = min(max(xc, 0), 1)
            yc = min(max(yc, 0), 1)
            w = min(max(w, 0), 1)
            h = min(max(h, 0), 1)
            lines.append(f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
        with open(lbl_out, "w") as f:
            f.write("\n".join(lines))
        return split

    results = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        for r in ex.map(process, chosen):
            results.append(r)

    n_train = sum(1 for r in results if r == "train")
    n_val = sum(1 for r in results if r == "val")
    n_fail = sum(1 for r in results if r is None)
    print(f"train={n_train} val={n_val} fail={n_fail}")

    yaml_path = os.path.join(OUT, "data.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {OUT}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("names:\n")
        for i, name in enumerate(CLASS_NAMES):
            f.write(f"  {i}: {name}\n")
    print("wrote", yaml_path)

    # --- 문서화용 클래스 분포 요약 (인스턴스 수 기준, train/val 분리) ---
    def count_instances(items):
        cnt = {name: 0 for name in CLASS_NAMES}
        img_cnt = {name: 0 for name in CLASS_NAMES}
        for s in items:
            dets = (s.get("detections") or {}).get("detections", [])
            seen = set()
            for d in dets:
                label = d["label"]
                if label not in CLASS_MAP:
                    continue
                cnt[label] += 1
                seen.add(label)
            for label in seen:
                img_cnt[label] += 1
        return cnt, img_cnt

    train_inst, train_img = count_instances(train_set)
    val_inst, val_img = count_instances(val_set)
    dist = {
        "n_total": len(chosen),
        "n_train": len(train_set),
        "n_val": len(val_set),
        "rare_union_images": len(rare_union_ids),
        "train_class_images_in_full_10k": len(train_imgs),
        "instances_train": train_inst,
        "instances_val": val_inst,
        "images_containing_class_train": train_img,
        "images_containing_class_val": val_img,
    }
    dist_path = os.path.join(OUT, "class_distribution.json")
    with open(dist_path, "w") as f:
        json.dump(dist, f, indent=2, ensure_ascii=False)
    print("wrote", dist_path)
    print(json.dumps(dist, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

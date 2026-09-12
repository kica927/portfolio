import json, random, os, sys
from concurrent.futures import ThreadPoolExecutor
import urllib.request

random.seed(42)

BASE = os.path.expanduser("~/portfolio_autonomous/perception")
SAMPLES_JSON = os.path.join(BASE, "data", "samples.json")
OUT = os.path.join(BASE, "data", "bdd_subset")
N_TOTAL = 1000
N_VAL = 200

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

def main():
    data = json.load(open(SAMPLES_JSON))["samples"]
    random.shuffle(data)
    chosen = data[:N_TOTAL]

    for split in ("images/train", "images/val", "labels/train", "labels/val"):
        os.makedirs(os.path.join(OUT, split), exist_ok=True)

    val_set = set(id(s) for s in chosen[:N_VAL])

    def process(item):
        s = item
        filepath = s["filepath"]  # e.g. data/xxx.jpg
        fname = os.path.basename(filepath)
        stem = os.path.splitext(fname)[0]
        split = "val" if id(s) in val_set else "train"
        img_out = os.path.join(OUT, "images", split, fname)
        lbl_out = os.path.join(OUT, "labels", split, stem + ".txt")

        if not os.path.exists(img_out):
            url = HF_RESOLVE + filepath
            try:
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
        f.write(f"names:\n")
        for i, name in enumerate(CLASS_NAMES):
            f.write(f"  {i}: {name}\n")
    print("wrote", yaml_path)

if __name__ == "__main__":
    main()

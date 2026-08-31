"""A1 — INT8(NNCF) 양자화 + FP32 대비 정확도(mAP)/지연/크기 비교.
best.pt(YOLO11n) -> OpenVINO FP32 IR / INT8 IR(NNCF PTQ, 복원 데이터셋 캘리브레이션)
val 500장(복원 라벨)으로 mAP 측정, CPU 지연(난수 N=100), 모델 크기 비교.
"""
import time, statistics, pathlib, sys
import numpy as np

HERE = pathlib.Path(__file__).parent
BEST = HERE/"best.pt"
DATA = pathlib.Path.home()/"Desktop/intel/_a1_dataset/dataset/data.yaml"
IMG  = 640
N, WARMUP = 100, 15

def export_ir(int8):
    from ultralytics import YOLO
    m = YOLO(str(BEST))
    kw = dict(format="openvino", imgsz=IMG)
    if int8:
        kw.update(int8=True, data=str(DATA))
    p = pathlib.Path(m.export(**kw))
    return p if p.is_dir() else p.parent

def dir_size_mb(d):
    return sum(f.stat().st_size for f in pathlib.Path(d).glob("*") if f.is_file())/1e6

def map_eval(ir_dir, tag):
    from ultralytics import YOLO
    mv = YOLO(str(ir_dir), task="detect")
    r = mv.val(data=str(DATA), imgsz=IMG, split="val", verbose=False, plots=False)
    print(f"[MAP {tag}] mAP50-95={r.box.map:.4f}  mAP50={r.box.map50:.4f}  mAP75={r.box.map75:.4f}")
    return r.box.map, r.box.map50

def latency(ir_dir, tag):
    import openvino as ov
    core = ov.Core()
    xml = next(pathlib.Path(ir_dir).glob("*.xml"))
    cm = core.compile_model(str(xml), "CPU")
    x = np.random.rand(1,3,IMG,IMG).astype(np.float32)
    for _ in range(WARMUP): cm(x)
    ts=[]
    for _ in range(N):
        t=time.perf_counter(); cm(x); ts.append((time.perf_counter()-t)*1000)
    ts.sort()
    mean=statistics.mean(ts)
    print(f"[LAT {tag}] mean={mean:.1f}ms p95={ts[int(N*0.95)]:.1f} fps={1000/mean:.1f}")
    return mean, 1000/mean

if __name__=="__main__":
    print("best.pt:", BEST, f"({BEST.stat().st_size/1e6:.2f} MB)")
    print("data:", DATA)
    results={}
    for int8 in (False, True):
        tag = "INT8" if int8 else "FP32"
        print(f"\n===== {tag} IR export =====")
        ir = export_ir(int8)
        print(f"[{tag}] IR dir: {ir}  size={dir_size_mb(ir):.2f} MB")
        mp, mp50 = map_eval(ir, tag)
        lat, fps = latency(ir, tag)
        results[tag]=dict(size=dir_size_mb(ir), map=mp, map50=mp50, lat=lat, fps=fps)
    print("\n============ A1 요약 ============")
    print(f"{'cfg':5} {'size_MB':>8} {'mAP50-95':>9} {'mAP50':>7} {'CPU_ms':>7} {'CPU_fps':>8}")
    for k in ("FP32","INT8"):
        r=results[k]
        print(f"{k:5} {r['size']:8.2f} {r['map']:9.4f} {r['map50']:7.4f} {r['lat']:7.1f} {r['fps']:8.1f}")
    f=results['FP32']; i=results['INT8']
    print(f"\nINT8 vs FP32: size {i['size']/f['size']*100:.0f}%  "
          f"mAP50-95 델타 {(i['map']-f['map'])*100:+.2f}pp  "
          f"지연 {f['lat']/i['lat']:.2f}x")

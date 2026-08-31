"""A1 — best.pt OpenVINO 엣지 최적화 · 1차 슬라이스: 맥 arm64 CPU 지연 벤치.

best.pt -> OpenVINO IR(FP32/FP16) 변환 후 CPU 추론 지연을 측정한다.
INT8(NNCF)·Arc GPU 벤치는 캘리브레이션셋/데스크탑 전송이 필요해 다음 단계.

    ~/Desktop/intel/.venv_a1/bin/python a1_bench_cpu.py
"""
import time, statistics, pathlib, sys
import numpy as np

BEST = pathlib.Path.home()/"Desktop/intel/_작업_grippers/best.pt"
OUT  = pathlib.Path.home()/"Desktop/intel/_a1_ir"
N, WARMUP = 100, 15

def export(fmt_half):
    from ultralytics import YOLO
    m = YOLO(str(BEST))
    p = m.export(format="openvino", half=fmt_half, imgsz=640)
    return pathlib.Path(p)

def bench(ir_dir, tag):
    import openvino as ov
    core = ov.Core()
    xml = next(pathlib.Path(ir_dir).glob("*.xml"))
    cm = core.compile_model(str(xml), "CPU")
    inp = cm.inputs[0]
    shape = [d if d>0 else 1 for d in inp.get_partial_shape().get_max_shape()] if inp.get_partial_shape().is_dynamic else list(inp.shape)
    x = np.random.rand(*shape).astype(np.float32)
    for _ in range(WARMUP): cm(x)
    ts=[]
    for _ in range(N):
        t=time.perf_counter(); cm(x); ts.append((time.perf_counter()-t)*1000)
    ts.sort()
    print(f"[{tag}] shape={shape}  mean={statistics.mean(ts):.1f}ms  "
          f"p50={ts[len(ts)//2]:.1f}  p95={ts[int(len(ts)*0.95)]:.1f}  "
          f"throughput={1000/statistics.mean(ts):.1f} fps")

if __name__=="__main__":
    assert BEST.exists(), BEST
    print("best.pt:", BEST, f"({BEST.stat().st_size/1e6:.1f} MB)")
    for half in (False, True):
        tag = "OVIR-FP16-CPU" if half else "OVIR-FP32-CPU"
        try:
            ir = export(half)
            bench(ir, tag)
        except Exception as e:
            print(f"[{tag}] 실패: {e}")

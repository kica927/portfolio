"""A1 데스크탑 벤치 — CPU · iGPU(GPU.0) · Arc B580(GPU.1), FP32/FP16 지연.
    ~/.venv_a1/bin/python a1_bench_gpu_desktop.py ~/a1_ir_fp32/best.xml
"""
import time, statistics, sys, pathlib
import numpy as np, openvino as ov
IR = sys.argv[1] if len(sys.argv) > 1 else str(pathlib.Path.home()/"a1_ir_fp32/best.xml")
N, WARM = 100, 20
core = ov.Core(); model = core.read_model(IR)
x = np.random.rand(1, 3, 640, 640).astype(np.float32)
plans = [("CPU","f32"),("CPU","f16"),("GPU.0","f16"),("GPU.1","f32"),("GPU.1","f16")]
print(f"IR={IR}")
print(f"{'device':7} {'prec':4} {'mean_ms':>8} {'p95_ms':>7} {'fps':>7}  name")
for dev, prec in plans:
    try:
        cm = core.compile_model(model, dev, {"INFERENCE_PRECISION_HINT": prec})
        for _ in range(WARM): cm(x)
        ts = []
        for _ in range(N):
            t = time.perf_counter(); cm(x); ts.append((time.perf_counter()-t)*1000)
        ts.sort()
        name = core.get_property(dev, "FULL_DEVICE_NAME")
        print(f"{dev:7} {prec:4} {statistics.mean(ts):8.2f} {ts[int(N*0.95)]:7.2f} {1000/statistics.mean(ts):7.1f}  {name}")
    except Exception as e:
        print(f"{dev:7} {prec:4}  실패: {str(e)[:70]}")

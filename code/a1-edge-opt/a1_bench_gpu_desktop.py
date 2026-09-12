"""A1 데스크탑 벤치 — CPU · iGPU(GPU.0) · Arc B580(GPU.1) · NPU, FP32/FP16 지연.
NPU: Intel Core Ultra 5 225 내장 NPU(/dev/accel0). 미인식/실패 시 예외 메시지를 그대로
출력한다(정직 기록 — 실패를 감추지 않는다).
    ~/a1venv/bin/python a1_bench_gpu_desktop.py [IR.xml IR2.xml ...]
    인자 없으면 FP32 IR과 INT8 IR을 기본으로 순회한다.
"""
import time, statistics, sys, pathlib
import numpy as np, openvino as ov

DEFAULT_IRS = [
    str(pathlib.Path.home() / "a1_ir_fp32/best.xml"),
    str(pathlib.Path.home() / "a1_ir/best_int8_openvino_model/best.xml"),
]
IRS = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_IRS
N, WARM = 100, 20
core = ov.Core()
x = np.random.rand(1, 3, 640, 640).astype(np.float32)
plans = [
    ("CPU", "f32"), ("CPU", "f16"),
    ("GPU.0", "f16"),
    ("GPU.1", "f32"), ("GPU.1", "f16"),
    ("NPU", "f16"), ("NPU", "f32"),
]
print(f"available_devices={core.available_devices}")
for IR in IRS:
    model = core.read_model(IR)
    print(f"\nIR={IR}")
    print(f"{'device':7} {'prec':4} {'mean_ms':>8} {'p95_ms':>7} {'fps':>7}  name")
    for dev, prec in plans:
        try:
            cm = core.compile_model(model, dev, {"INFERENCE_PRECISION_HINT": prec})
            for _ in range(WARM): cm(x)
            ts = []
            for _ in range(N):
                t = time.perf_counter(); cm(x); ts.append((time.perf_counter() - t) * 1000)
            ts.sort()
            name = core.get_property(dev, "FULL_DEVICE_NAME")
            print(f"{dev:7} {prec:4} {statistics.mean(ts):8.2f} {ts[int(N*0.95)]:7.2f} {1000/statistics.mean(ts):7.1f}  {name}")
        except Exception as e:
            msg = " ".join(str(e).split())
            print(f"{dev:7} {prec:4}  실패: {msg[:220]}")

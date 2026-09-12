"""
2단계: 1단계에서 나온 ONNX(예상외로 export 성공)를 OpenVINO IR로 변환하고,
CPU/Arc B580에서 지연을 측정해 PyTorch/XPU 베이스라인(143.64ms)과 비교한다.

실행 위치: 원격 Ubuntu 데스크탑
    source ~/a1venv/bin/activate
    python step2_convert_and_bench.py
"""
import statistics
import time

import numpy as np
import openvino as ov

ONNX_PATH = "/home/lemma/smolvla_openvino_experiment/full_pipeline.onnx"
IR_PATH = "/home/lemma/smolvla_openvino_experiment/full_pipeline_ir.xml"

core = ov.Core()
print("available_devices:", core.available_devices)

model = core.read_model(ONNX_PATH)
ov.save_model(model, IR_PATH)
print("SUCCESS: OpenVINO IR 변환 완료")
print("inputs:", [(i.get_any_name(), i.get_partial_shape()) for i in model.inputs])
print("outputs:", [o.get_any_name() for o in model.outputs])

# 파라미터(가중치) 총량 확인 - export가 실제로 전체 가중치를 담았는지 검증
total_params = 0
for node in model.get_ordered_ops():
    if node.get_type_name() == "Constant":
        total_params += node.get_output_tensor(0).size
print(f"ONNX IR 내 Constant 텐서 총 원소 수: {total_params:,} (~{total_params / 1e6:.1f}M)")
print("(참고: 원본 SmolVLA 전체 파라미터는 450.0M — 위 수치와 불일치하면 export가")
print(" 원본과 동일한 계산을 하는지 의심해야 한다. 출력값 자체는 대조 검증하지 않았다.)")
print()

dummy_inputs = {
    "image0": np.random.rand(1, 3, 512, 512).astype(np.float32),
    "img_mask0": np.array([True]),
    "lang_tokens": np.random.randint(0, 1000, (1, 48)).astype(np.int64),
    "lang_masks": np.ones((1, 48)).astype(np.bool_),
    "state": np.random.rand(1, 32).astype(np.float32),
}

for dev in ["CPU", "GPU.1"]:
    try:
        cm = core.compile_model(model, dev)
        for _ in range(5):
            cm(dummy_inputs)
        times_ms = []
        for _ in range(20):
            t0 = time.perf_counter()
            cm(dummy_inputs)
            times_ms.append((time.perf_counter() - t0) * 1000)
        print(f"{dev}: mean {statistics.mean(times_ms):.2f}ms median {statistics.median(times_ms):.2f}ms")
    except Exception as e:
        print(f"{dev} 실패: {str(e)[:300]}")

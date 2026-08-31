#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
set -e
uv venv ~/a2venv >/dev/null 2>&1
source ~/a2venv/bin/activate
echo "=== install torch-xpu + ultralytics ==="
uv pip install -q torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/xpu 2>&1 | tail -2
uv pip install -q ultralytics 2>&1 | tail -2
python -c "import torch,ultralytics;print('torch',torch.__version__,'xpu_avail',torch.xpu.is_available());print('ultralytics',ultralytics.__version__)"
echo "=== SMOKE: 1 epoch, fraction 0.05, device=xpu ==="
cd ~/a2_dataset/dataset
yolo detect train model=yolo11n.pt data=data.yaml epochs=1 imgsz=640 device=xpu \
  fraction=0.05 batch=16 workers=4 name=smoke project="$HOME/a2_runs" exist_ok=true plots=False 2>&1 | tail -20
echo "SETUP_SMOKE_DONE exit=$?"

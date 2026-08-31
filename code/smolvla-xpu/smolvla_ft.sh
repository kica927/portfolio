#!/bin/bash
cd "$HOME/lerobot" || exit 1
export HF_USER=kica927
"$HOME/lerobot/.venv/bin/lerobot-train" \
  --policy.path=lerobot/smolvla_base \
  --policy.device=xpu \
  --policy.push_to_hub=false \
  --rename_map='{"observation.images.followcam":"observation.images.camera1"}' \
  --dataset.repo_id=kica927/redball \
  --dataset.root="$HOME/.cache/huggingface/lerobot/kica927/redball" \
  --batch_size=4 \
  --steps=6000 \
  --save_freq=3000 \
  --log_freq=50 \
  --wandb.enable=false \
  --output_dir="$HOME/smolvla_redball_ft"
echo "SMOLVLA_FT_DONE exit=$?"

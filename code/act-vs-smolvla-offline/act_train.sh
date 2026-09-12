#!/bin/bash
# ACT를 kica927/redball(빨간 공, 15ep/8645프레임)로 처음부터(from scratch) 학습.
# smolvla_ft.sh(code/smolvla-xpu/smolvla_ft.sh)와 같은 조건(같은 데이터셋, batch_size=4,
# XPU, wandb 끔)으로 맞추되, ACT는 사전학습 체크포인트가 없어 rename_map이 필요 없다
# (ACT는 데이터셋에 있는 카메라 키를 그대로 학습 시 자동으로 반영한다).
#
# steps=20000 근거: LeRobot 공식 cheat-sheet(docs/source/cheat-sheet.mdx)가 so101류
# 로봇에서 ACT를 처음부터 학습할 때 기본값으로 제시하는 값. SmolVLA는 사전학습
# 체크포인트를 파인튜닝(6000 step)하지만 ACT는 랜덤 초기화에서 시작하므로 같은
# step 수로는 수렴이 불리하다 — "같은 step 예산"이 아니라 "각자에게 합리적인 학습
# 예산"으로 맞췄다(정확한 근거는 문서의 Method 절 참고).
cd "$HOME/lerobot" || exit 1
export HF_USER=kica927
"$HOME/lerobot/.venv/bin/lerobot-train" \
  --policy.type=act \
  --policy.device=xpu \
  --policy.push_to_hub=false \
  --dataset.repo_id=kica927/redball \
  --dataset.root="$HOME/.cache/huggingface/lerobot/kica927/redball" \
  --batch_size=4 \
  --steps=20000 \
  --save_freq=5000 \
  --log_freq=50 \
  --wandb.enable=false \
  --output_dir="$HOME/act_redball_ft"
echo "ACT_FT_DONE exit=$?"

"""
ACT vs SmolVLA 추론 지연(단일 관측 -> 액션 출력) 벤치마크.
실기 SO-ARM101 없이, 더미 이미지/상태로만 정책의 select_action() 1회 호출 시간을 잰다.
매 반복 전에 policy.reset()을 호출해 액션 큐를 비운다 - 그래야 청크 정책(ACT/SmolVLA)이
매번 "큐에서 꺼내기"가 아니라 실제 forward를 다시 계산하게 되어, 두 정책의 순수 추론
비용을 공평하게 비교할 수 있다.

실행 위치: 원격 Ubuntu 데스크탑, ~/lerobot/.venv/bin/python bench_latency.py
"""

import json
import statistics
import time

import numpy as np
import torch

from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.utils import prepare_observation_for_inference

DEVICE = "xpu"
N_WARMUP = 5
N_ITERS = 30


def count_params(policy):
    total = sum(p.numel() for p in policy.parameters())
    trainable = sum(p.numel() for p in policy.parameters() if p.requires_grad)
    return total, trainable


def bench(name, policy_cls, pretrained_path, image_key, task):
    policy = policy_cls.from_pretrained(pretrained_path)
    policy.to(DEVICE)
    policy.eval()
    total_params, trainable_params = count_params(policy)

    preprocessor, postprocessor = make_pre_post_processors(
        policy.config, pretrained_path=pretrained_path
    )

    dummy_image = (np.random.rand(480, 640, 3) * 255).astype(np.uint8)
    dummy_state = np.random.rand(6).astype(np.float32)

    times_ms = []
    for i in range(N_WARMUP + N_ITERS):
        obs = {
            f"observation.images.{image_key}": dummy_image.copy(),
            "observation.state": dummy_state.copy(),
        }
        policy.reset()
        with torch.inference_mode():
            obs_t = prepare_observation_for_inference(obs, torch.device(DEVICE), task, "so_follower")
            obs_t = preprocessor(obs_t)
            torch.xpu.synchronize()
            t0 = time.perf_counter()
            action = policy.select_action(obs_t)
            torch.xpu.synchronize()
            t1 = time.perf_counter()
            _ = postprocessor(action)
        if i >= N_WARMUP:
            times_ms.append((t1 - t0) * 1000.0)

    result = {
        "name": name,
        "pretrained_path": pretrained_path,
        "total_params": total_params,
        "trainable_params": trainable_params,
        "n_iters": N_ITERS,
        "latency_ms_mean": statistics.mean(times_ms),
        "latency_ms_median": statistics.median(times_ms),
        "latency_ms_stdev": statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0,
        "latency_ms_min": min(times_ms),
        "latency_ms_max": max(times_ms),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    act_result = bench(
        "ACT",
        ACTPolicy,
        "/home/lemma/act_redball_ft/checkpoints/020000/pretrained_model",
        image_key="followcam",
        task="",
    )
    smolvla_result = bench(
        "SmolVLA",
        SmolVLAPolicy,
        "/home/lemma/smolvla_redball_ft/checkpoints/006000/pretrained_model",
        image_key="camera1",
        task="pick up the red ball and place it somewhere",
    )

    with open("/home/lemma/act_vs_smolvla_latency.json", "w") as f:
        json.dump([act_result, smolvla_result], f, indent=2, ensure_ascii=False)
    print("WROTE /home/lemma/act_vs_smolvla_latency.json")

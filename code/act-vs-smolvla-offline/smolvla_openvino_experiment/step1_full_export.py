"""
1단계: SmolVLA 전체 파이프라인(select_action) ONNX export 시도.
DynamicCache, 리스트 입력, 조건분기가 얼마나 export를 막는지 정확한 에러로 확인한다.
"""
import traceback

import numpy as np
import torch

from lerobot.policies.factory import make_pre_post_processors
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.utils import prepare_observation_for_inference

CKPT = "/home/lemma/smolvla_redball_ft/checkpoints/006000/pretrained_model"
DEVICE = "xpu"  # CPU로 시도하면 vlm_with_expert 내부 buffer가 xpu에 남아 device mismatch가 나서 xpu로 통일

policy = SmolVLAPolicy.from_pretrained(CKPT)
policy.to(DEVICE)
policy.eval()

preprocessor, postprocessor = make_pre_post_processors(policy.config, pretrained_path=CKPT)

dummy_image = (np.random.rand(480, 640, 3) * 255).astype(np.uint8)
dummy_state = np.random.rand(6).astype(np.float32)
obs = {
    "observation.images.camera1": dummy_image.copy(),
    "observation.state": dummy_state.copy(),
}
policy.reset()
obs_t = prepare_observation_for_inference(obs, torch.device(DEVICE), "pick up the red ball and place it somewhere", "so_follower")
obs_t = preprocessor(obs_t)

images, img_masks = policy.prepare_images(obs_t)
state = policy.prepare_state(obs_t)
lang_tokens = obs_t["observation.language.tokens"]
lang_masks = obs_t["observation.language.attention_mask"]


class SampleActionsWrapper(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, image0, img_mask0, lang_tokens, lang_masks, state):
        return self.model.sample_actions([image0], [img_mask0], lang_tokens, lang_masks, state)


wrapper = SampleActionsWrapper(policy.model)
wrapper.eval()

print("=== 1a. torch.onnx.export (legacy TorchScript exporter) ===")
try:
    torch.onnx.export(
        wrapper,
        (images[0], img_masks[0], lang_tokens, lang_masks, state),
        "/home/lemma/smolvla_openvino_experiment/full_pipeline.onnx",
        input_names=["image0", "img_mask0", "lang_tokens", "lang_masks", "state"],
        output_names=["actions"],
        opset_version=18,
    )
    print("SUCCESS: full pipeline exported (unexpected)")
except Exception as e:
    print("FAILED as expected.")
    print(f"Exception type: {type(e).__name__}")
    print(f"Message: {e}")
    traceback.print_exc()

print()
print("=== 1b. torch.onnx.export(..., dynamo=True) ===")
try:
    torch.onnx.export(
        wrapper,
        (images[0], img_masks[0], lang_tokens, lang_masks, state),
        "/home/lemma/smolvla_openvino_experiment/full_pipeline_dynamo.onnx",
        input_names=["image0", "img_mask0", "lang_tokens", "lang_masks", "state"],
        output_names=["actions"],
        dynamo=True,
    )
    print("SUCCESS: full pipeline exported via dynamo (unexpected)")
except Exception as e:
    print("FAILED as expected.")
    print(f"Exception type: {type(e).__name__}")
    print(f"Message: {e}")
    traceback.print_exc()

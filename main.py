import os
import random
from os import path
from contextlib import nullcontext
import time

cache_path = path.join(path.dirname(path.abspath(__file__)), "models")

os.environ["TRANSFORMERS_CACHE"] = cache_path
os.environ["HF_HUB_CACHE"] = cache_path
os.environ["HF_HOME"] = cache_path
use_cuda_local = os.environ.get("USE_LOCAL_CUDA", False)

class timer:
    def __init__(self, method_name="timed process"):
        self.method = method_name

    def __enter__(self):
        self.start = time.time()
        print(f"{self.method} starts")

    def __exit__(self, exc_type, exc_val, exc_tb):
        end = time.time()
        print(f"{self.method} took {str(round(end - self.start, 2))}s")


def load_models(is_local=False):
    import torch
    from diffusers import AutoPipelineForImage2Image, LCMScheduler
    from diffusers.utils import load_image

    if not is_local:
        torch.backends.cuda.matmul.allow_tf32 = True

    model_id = "Lykon/dreamshaper-7"
    lcm_lora_id = "latent-consistency/lcm-lora-sdv1-5"

    pipe = AutoPipelineForImage2Image.from_pretrained(
        model_id,
        cache_dir=cache_path,
        torch_dtype=torch.float16,
        variant="fp16",
        safety_checker=None
    )

    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)

    pipe.load_lora_weights(lcm_lora_id)
    pipe.fuse_lora()

    device = "cuda" if not is_local or use_cuda_local else "mps"

    pipe.to(device=device)

    generator = torch.Generator()

    def infer(
            prompt,
            image,
            num_inference_steps=4,
            guidance_scale=1,
            strength=0.9,
            seed=random.randrange(0, 2**63)
    ):
        with torch.inference_mode():
            with torch.autocast("cuda") if device == "cuda" else nullcontext():
                with timer("inference"):
                    return pipe(
                        prompt=prompt,
                        image=load_image(image),
                        generator=generator.manual_seed(seed),
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        strength=strength
                    ).images[0]

    return infer
"""Torch device discovery for audio providers."""

import torch


def get_device_map() -> dict[str, str]:
    """Return a dict mapping human-readable device labels to torch device strings (cpu + any CUDA GPUs)."""
    device_map = {"cpu": "cpu"}
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            label = f"cuda:{i} - {torch.cuda.get_device_name(i)}"
            device_map[label] = f"cuda:{i}"
    return device_map

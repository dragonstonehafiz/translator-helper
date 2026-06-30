import pysubs2
import json
import torch

def load_json(filepath: str):
    """Load and return parsed JSON from a file path."""
    json_file = open(filepath)
    json_data = json.load(json_file)

    return json_data


def load_sub_data(filepath: str, include_speaker: bool = True):
    """Load a subtitle file and return each line as a plain string, optionally prefixed with the speaker name."""
    subs = pysubs2.load(filepath)
    output_list = []
    for line in subs:
        line: pysubs2.SSAEvent
        if include_speaker:
            text = f"{line.name}: {line.text}"
        else:
            text = line.text
        output_list.append(text)

    return output_list


def get_device_map():
    """Return a dict mapping human-readable device labels to torch device strings (cpu + any CUDA GPUs)."""
    device_map = {"cpu": "cpu"}
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            label = f"cuda:{i} - {torch.cuda.get_device_name(i)}"
            device_map[label] = f"cuda:{i}"
    return device_map
    
    

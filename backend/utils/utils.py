import pysubs2
import json

def load_json(filepath: str):
    json_file = open(filepath)
    json_data = json.load(json_file)
    
    return json_data
    

def load_sub_data(filepath: str, include_speaker: bool = True):
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
    
    
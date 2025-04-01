import openai
import whisper
import torch

# To remove FutureWarning
import functools
whisper.torch.load = functools.partial(whisper.torch.load, weights_only=True)

def load_whisper_model(selected_model: str = None, enable_cuda: bool = False): 
    device = "cuda" if enable_cuda else "cpu"
    try:
        model = whisper.load_model(selected_model, device=device)
    except torch.cuda.OutOfMemoryError:
        return None
    return model

def test_api_key(api_key):
    try:
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
    except openai.OpenAIError:
        return False
    return True

def create_client(api_key: str = None):
    if api_key is None:
        api_key = input("Please enter your API key:")
    client = openai.OpenAI(api_key=api_key)
    return client

import whisper
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search.tool import TavilySearchResults
import os
import torch

def get_device_map():
    device_map = {"cpu": "cpu"}
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            label = f"cuda:{i} - {torch.cuda.get_device_name(i)}"
            device_map[label] = f"cuda:{i}"
    return device_map


def load_whisper_model(model_name: str = "medium", device: str = "cpu"):
    """Load a Whisper model by name using the whisper package."""
    torch.cuda.empty_cache()
    return whisper.load_model(model_name, device=device)


def load_gpt_model(api_key: str, model_name: str = "gpt-4o", temperature: float = 0.5):
    llm = ChatOpenAI(api_key=api_key, model=model_name, temperature=temperature)
    return llm
    
    
def load_web_searcher(api_key: str):
    os.environ["TAVILY_API_KEY"] = api_key
    search_tool = TavilySearchResults(k=3)
    return search_tool

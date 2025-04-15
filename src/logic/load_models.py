import whisper
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search.tool import TavilySearchResults
import os

def load_whisper_model(model_name: str = "medium"):
    """Load a Whisper model by name using the whisper package."""
    return whisper.load_model(model_name)


def load_gpt_model(api_key: str, model_name: str = "gpt-4o", temperature: float = 0.5):
    llm = ChatOpenAI(api_key=api_key, model=model_name, temperature=temperature)
    return llm
    
    
def load_web_searcher(api_key: str):
    os.environ["TAVILY_API_KEY"] = api_key
    search_tool = TavilySearchResults(k=3)
    return search_tool
    
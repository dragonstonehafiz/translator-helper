from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import openai

from interface.llm_interface import LLMInterface


class LLM_ChatGPT(LLMInterface):
    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: str | None = None
    ):
        self._model_name = model_name
        self._device = "API"
        self._api_key = api_key
        self._temperature = 0.5
        self._running = False
        self._llm = None

    def configure(self, settings: dict):
        if not settings:
            return

        if "api_key" in settings:
            self._api_key = settings["api_key"]
        if "model_name" in settings:
            self._model_name = settings["model_name"]
        if "temperature" in settings:
            self._temperature = settings["temperature"]

    def initialize(self):
        self._llm = self._build_llm()

    def change_model(self, model_name: str):
        self._model_name = model_name
        if self._llm is not None:
            self._llm = self._build_llm()
            
    def get_model(self) -> str:
        return self._model_name

    def set_device(self, device: str):
        self._device = "API"

    def get_device(self) -> str:
        return self._device

    def set_temperature(self, temperature: float):
        self._temperature = temperature

    def get_temperature(self) -> float:
        return self._temperature

    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None
    ):
        llm = self._llm
        if llm is None:
            llm = self._build_llm()

        if temperature is not None or max_tokens is not None:
            llm = self._build_llm(temperature=temperature, max_tokens=max_tokens)

        messages = [HumanMessage(content=prompt)]
        if system_prompt:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]

        response = llm.invoke(messages)
        return response.content

    def shutdown(self):
        self._llm = None

    def is_ready(self) -> bool:
        if not self._api_key:
            return False
        return self._validate_api_key()

    def is_running(self) -> bool:
        return self._running

    def set_running(self, running: bool):
        self._running = running

    def _build_llm(self, temperature: float | None = None, max_tokens: int | None = None):
        if not self._api_key:
            raise ValueError("OpenAI API key is required to initialize ChatGPT.")

        params = {
            "api_key": self._api_key,
            "model": self._model_name,
            "temperature": self._temperature if temperature is None else temperature
        }
        if max_tokens is None:
            pass
        else:
            params["max_tokens"] = max_tokens

        return ChatOpenAI(**params)

    def _validate_api_key(self) -> bool:
        try:
            client = openai.OpenAI(api_key=self._api_key)
            _ = client.models.list()
            return True
        except Exception:
            return False

import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from interface.llm_interface import LLMInterface


class LLMChatGPT(LLMInterface):
    def __init__(self):
        env_model = os.getenv("OPENAI_MODEL") or "gpt-4o"
        env_api_key = os.getenv("OPENAI_API_KEY") or ""
        env_temperature = os.getenv("OPENAI_TEMPERATURE")

        self._model_name = env_model
        self._device = "API"
        self._api_key = env_api_key
        self._temperature = float(env_temperature) if env_temperature else 0.5
        self._running = False
        self._llm = None
        self._status = "not_loaded"

    def configure(self, settings: dict):
        if not settings:
            return

        if "api_key" in settings:
            self._api_key = settings["api_key"]
        if "model_name" in settings:
            self._model_name = settings["model_name"]
        if "temperature" in settings:
            self._temperature = settings["temperature"]

    def get_settings_schema(self) -> dict:
        return {
            "provider": "llm_chatgpt",
            "title": "OpenAI ChatGPT",
            "fields": [
                {
                    "key": "model_name",
                    "label": "Model",
                    "type": "select",
                    "options": [
                        {"label": "gpt-4.1-mini", "value": "gpt-4.1-mini"},
                        {"label": "gpt-4.1", "value": "gpt-4.1"},
                        {"label": "gpt-5.1", "value": "gpt-5.1"},
                        {"label": "gpt-4o", "value": "gpt-4o"},
                        {"label": "o4-mini", "value": "o4-mini"}
                    ],
                    "default": self._model_name,
                    "required": True
                },
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "password",
                    "placeholder": "sk-...",
                    "required": True
                },
                {
                    "key": "temperature",
                    "label": "Temperature",
                    "type": "number",
                    "min": 0,
                    "max": 2,
                    "step": 0.1,
                    "default": self._temperature
                }
            ]
        }

    def initialize(self):
        try:
            self._llm = self._build_llm()
            self._status = "loaded"
        except Exception:
            self._status = "error"
            raise

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

    def get_server_variables(self) -> dict:
        return {
            "openai_model": self._model_name,
            "temperature": self._temperature
        }

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
        self._status = "not_loaded"

    def get_status(self) -> str:
        return self._status

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

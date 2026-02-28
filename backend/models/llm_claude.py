import json
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from interface import LLMInterface


class LLMClaude(LLMInterface):
    CONFIG_FILE = "llm_claude.json"

    def __init__(self):
        self._model_name = "claude-sonnet-4-6"
        self._device = "API"
        self._api_key = ""
        self._temperature = 0.5
        self._running = False
        self._llm = None
        self._status = "not_loaded"

        _data_path = self._get_config_path(self.CONFIG_FILE)
        if os.path.isfile(_data_path):
            with open(_data_path, "r", encoding="utf-8") as _f:
                _cfg = json.load(_f)
            self._model_name = _cfg.get("model_name", self._model_name)
            self._api_key = _cfg.get("api_key", self._api_key)
            self._temperature = float(_cfg.get("temperature", self._temperature))
        else:
            os.makedirs(os.path.dirname(_data_path), exist_ok=True)
            with open(_data_path, "w", encoding="utf-8") as _f:
                json.dump({"model_name": self._model_name, "api_key": "", "temperature": self._temperature}, _f, indent=2)

    def configure(self, settings: dict):
        if not settings:
            return

        if "api_key" in settings:
            self._api_key = settings["api_key"]
        if "model_name" in settings:
            self._model_name = settings["model_name"]
        if "temperature" in settings:
            self._temperature = settings["temperature"]

        _data_path = self._get_config_path(self.CONFIG_FILE)
        os.makedirs(os.path.dirname(_data_path), exist_ok=True)
        with open(_data_path, "w", encoding="utf-8") as _f:
            json.dump({"model_name": self._model_name, "api_key": self._api_key, "temperature": self._temperature}, _f, indent=2)

    def get_settings_schema(self) -> dict:
        return {
            "provider": "llm_claude",
            "title": "Anthropic Claude",
            "fields": [
                {
                    "key": "model_name",
                    "label": "Model",
                    "type": "select",
                    "options": [
                        {"label": "Claude Haiku 4.5", "value": "claude-haiku-4-5-20251001"},
                        {"label": "Claude Sonnet 4.6", "value": "claude-sonnet-4-6"},
                        {"label": "Claude Opus 4.6", "value": "claude-opus-4-6"},
                    ],
                    "default": self._model_name,
                    "required": True
                },
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "password",
                    "placeholder": "sk-ant-...",
                    "required": True
                },
                {
                    "key": "temperature",
                    "label": "Temperature",
                    "type": "number",
                    "min": 0,
                    "max": 1,
                    "step": 0.1,
                    "default": self._temperature
                }
            ]
        }

    def initialize(self):
        try:
            self._llm = self._build_llm()
            # Validate API key with a lightweight request.
            test_llm = self._build_llm(temperature=0, max_tokens=1)
            test_llm.invoke([HumanMessage(content="ping")])
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

    def get_server_variables(self) -> list[dict]:
        return [
            {"key": "anthropic_model", "label": "Model", "value": self._model_name},
            {"key": "temperature", "label": "Temperature", "value": self._temperature}
        ]

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
            raise ValueError("Anthropic API key is required to initialize Claude.")

        params = {
            "api_key": self._api_key,
            "model": self._model_name,
            "temperature": self._temperature if temperature is None else temperature,
            "max_tokens": max_tokens if max_tokens is not None else 8096
        }

        return ChatAnthropic(**params)

from __future__ import annotations

from typing import Optional
from llama_cpp import Llama
from interface.llm_interface import LLMInterface


class LLMLlamaCpp(LLMInterface):
    def __init__(
        self,
        model_path: str = "",
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        n_threads: int = 8,
        temperature: float = 0.5
    ):
        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._n_threads = n_threads
        self._temperature = temperature
        self._running = False
        self._llm: Optional[Llama] = None
        self._status = "not_loaded"

    def configure(self, settings: dict):
        if not settings:
            return

        if "model_path" in settings:
            self._model_path = str(settings["model_path"])
        if "n_ctx" in settings:
            self._n_ctx = int(settings["n_ctx"])
        if "n_gpu_layers" in settings:
            self._n_gpu_layers = int(settings["n_gpu_layers"])
        if "n_threads" in settings:
            self._n_threads = int(settings["n_threads"])
        if "temperature" in settings:
            self._temperature = float(settings["temperature"])

    def get_settings_schema(self) -> dict:
        return {
            "provider": "llm_llamacpp",
            "title": "Llama.cpp (GGUF)",
            "fields": [
                {
                    "key": "model_path",
                    "label": "Model Path",
                    "type": "text",
                    "placeholder": "C:\\models\\qwen2.5-7b-instruct-q4_k_m.gguf",
                    "required": True
                },
                {
                    "key": "n_ctx",
                    "label": "Context Size",
                    "type": "number",
                    "min": 512,
                    "max": 16384,
                    "step": 256,
                    "default": self._n_ctx
                },
                {
                    "key": "n_gpu_layers",
                    "label": "GPU Layers (-1 = auto)",
                    "type": "number",
                    "min": -1,
                    "max": 120,
                    "step": 1,
                    "default": self._n_gpu_layers,
                    "help": "How many model layers to offload to GPU. Higher = faster but uses more VRAM. -1 lets llama.cpp auto-select."
                },
                {
                    "key": "n_threads",
                    "label": "CPU Threads",
                    "type": "number",
                    "min": 1,
                    "max": 128,
                    "step": 1,
                    "default": self._n_threads,
                    "help": "Number of CPU threads used for inference. Set near your physical core count; too high can reduce responsiveness."
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
        self._model_path = model_name
        if self._llm is not None:
            self._llm = self._build_llm()

    def get_model(self) -> str:
        return self._model_path

    def set_device(self, device: str):
        # llama.cpp handles device via n_gpu_layers
        pass

    def get_device(self) -> str:
        return "local"

    def set_temperature(self, temperature: float):
        self._temperature = temperature

    def get_temperature(self) -> float:
        return self._temperature

    def get_server_variables(self) -> dict:
        return {
            "model_path": self._model_path,
            "n_ctx": self._n_ctx,
            "n_gpu_layers": self._n_gpu_layers,
            "n_threads": self._n_threads,
            "temperature": self._temperature
        }

    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None
    ):
        llm = self._llm or self._build_llm()
        final_prompt = prompt
        if system_prompt:
            final_prompt = f"{system_prompt}\n\n{prompt}"

        response = llm(
            final_prompt,
            temperature=self._temperature if temperature is None else temperature,
            max_tokens=max_tokens
        )
        return response["choices"][0]["text"].strip()

    def shutdown(self):
        self._llm = None
        self._status = "not_loaded"

    def get_status(self) -> str:
        return self._status

    def is_running(self) -> bool:
        return self._running

    def set_running(self, running: bool):
        self._running = running

    def _build_llm(self):
        if not self._model_path:
            raise ValueError("Model path is required to initialize Llama.cpp.")

        return Llama(
            model_path=self._model_path,
            n_ctx=self._n_ctx,
            n_gpu_layers=self._n_gpu_layers,
            n_threads=self._n_threads
        )

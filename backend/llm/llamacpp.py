from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Optional

from llama_cpp import Llama

from llm.interface import LLMInterface
from models.config import Choice, ConfigField, DropdownOption, IntegerOption, ModelConfig, NumberOption, setting
from models.state import ModelState

MODEL_DIR = Path(__file__).resolve().parents[1] / "model-files"


def _model_file_choices() -> tuple[Choice, ...]:
    """List the .gguf files in backend/model-files/ for the model dropdown."""
    if not MODEL_DIR.exists():
        return ()
    return tuple(
        Choice(entry.name, entry.name)
        for entry in sorted(MODEL_DIR.iterdir())
        if entry.is_file() and entry.suffix.lower() == ".gguf"
    )


@dataclass
class LlamaCppConfig(ModelConfig):
    """Settings for the local llama.cpp provider, saved to llm_llamacpp.json."""

    CONFIG_FILE: ClassVar[str] = "llm_llamacpp.json"
    PROVIDER: ClassVar[str] = "llm_llamacpp"
    TITLE: ClassVar[str] = "Llama.cpp (GGUF)"

    model_file: ConfigField[str] = setting("Model File", DropdownOption(_model_file_choices), "", required=True)
    n_ctx: ConfigField[int] = setting("Context Size", IntegerOption(min=512, max=16384, step=256), 4096)
    n_gpu_layers: ConfigField[int] = setting(
        "GPU Layers (-1 = auto)", IntegerOption(min=-1, max=120), -1,
        help="How many model layers to offload to GPU. Higher = faster but uses more VRAM. -1 lets llama.cpp auto-select.",
    )
    n_threads: ConfigField[int] = setting(
        "CPU Threads", IntegerOption(min=1, max=128), 8,
        help="Number of CPU threads used for inference. Set near your physical core count; too high can reduce responsiveness.",
    )
    temperature: ConfigField[float] = setting("Temperature", NumberOption(min=0, max=2, step=0.1), 0.5)


class LLMLlamaCpp(LLMInterface[LlamaCppConfig]):
    """LLM backend that runs a local GGUF model through llama.cpp."""

    def __init__(self):
        """Load the saved llama.cpp settings."""
        super().__init__(LlamaCppConfig.load())
        self._llm: Optional[Llama] = None

    def initialize(self) -> None:
        """Load the configured GGUF model."""
        try:
            self._llm = self._build_llm()
            self._state = ModelState.LOADED
        except Exception:
            self._llm = None
            self._state = ModelState.ERROR
            raise

    def shutdown(self) -> None:
        """Release the model."""
        self._llm = None
        self._state = ModelState.NOT_LOADED

    def infer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Run a chat completion with the loaded model."""
        if self._llm is None:
            raise RuntimeError("Llama.cpp model is not initialized.")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._llm.create_chat_completion(
            messages=messages,
            temperature=self._config.temperature.value if temperature is None else temperature,
            max_tokens=max_tokens,
        )
        return response["choices"][0]["message"]["content"].strip()

    def _build_llm(self) -> Llama:
        """Construct a Llama instance from the configured model file and runtime settings."""
        if not self._config.model_file.value:
            raise ValueError("Model file is required to initialize Llama.cpp.")

        return Llama(
            model_path=str(self._resolve_model_path(self._config.model_file.value)),
            n_ctx=self._config.n_ctx.value,
            n_gpu_layers=self._config.n_gpu_layers.value,
            n_threads=self._config.n_threads.value,
            verbose=False,
        )

    def _resolve_model_path(self, model_file: str) -> Path:
        """Resolve a model file name against backend/model-files/ unless it is already absolute."""
        path = Path(model_file)
        if path.is_absolute():
            return path
        return MODEL_DIR / model_file

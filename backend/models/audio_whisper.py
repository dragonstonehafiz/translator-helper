import os
from typing import Optional

import pysubs2
import whisper

from interface import AudioModelInterface


class AudioWhisper(AudioModelInterface):
    def __init__(self):
        env_model = os.getenv("WHISPER_MODEL") or "medium"
        env_device = os.getenv("WHISPER_DEVICE") or "cpu"

        self._model_name = env_model
        self._device = env_device
        self._model = None
        self._running = False
        self._status = "not_loaded"

    def configure(self, settings: dict):
        if not settings:
            return
        if "model_name" in settings:
            self._model_name = settings["model_name"]
        if "device" in settings:
            self._device = settings["device"]

    def get_settings_schema(self) -> dict:
        return {
            "provider": "audio_whisper",
            "title": "Whisper",
            "fields": [
                {
                    "key": "model_name",
                    "label": "Model",
                    "type": "select",
                    "options": [
                        {"label": "tiny", "value": "tiny"},
                        {"label": "base", "value": "base"},
                        {"label": "small", "value": "small"},
                        {"label": "medium", "value": "medium"},
                        {"label": "large", "value": "large"},
                        {"label": "turbo", "value": "turbo"}
                    ],
                    "default": self._model_name,
                    "required": True
                },
                {
                    "key": "device",
                    "label": "Device",
                    "type": "select",
                    "options": [
                        {"label": label, "value": value}
                        for label, value in self.get_available_devices().items()
                    ],
                    "default": self._device
                }
            ]
        }

    def initialize(self):
        try:
            self._model = self._build_model()
            self._status = "loaded"
        except Exception:
            self._status = "error"
            raise

    def change_model(self, model_name: str):
        self._model_name = model_name
        if self._model is not None:
            self._model = self._build_model()

    def transcribe_line(self, audio_path: str, language: str):
        if not os.path.isfile(audio_path):
            return "File not detected. Did you put the right path?"
        model = self._model or self._build_model()
        result = model.transcribe(audio_path, language=language)
        return result["text"]

    def transcribe_file(self, audio_path: str, language: str) -> pysubs2.SSAFile:
        if not os.path.isfile(audio_path):
            return "File not detected. Did you put the right path?"
        model = self._model or self._build_model()
        result = model.transcribe(audio_path, language=language)
        segments = result["segments"]

        subs = pysubs2.SSAFile()
        style = subs.styles["Default"]
        style.fontsize = 55
        style.fontname = "Arial"
        subs.styles["Default"] = style

        for seg in segments:
            line = pysubs2.SSAEvent(
                start=seg["start"] * 1000,
                end=seg["end"] * 1000,
                text=seg["text"]
            )
            subs.events.append(line)
        return subs

    def shutdown(self):
        self._model = None
        self._status = "not_loaded"

    def get_status(self) -> str:
        return self._status

    def get_model(self) -> str:
        return self._model_name

    def is_running(self) -> bool:
        return self._running

    def set_running(self, running: bool):
        self._running = running

    def set_device(self, device: str):
        self._device = device

    def get_device(self) -> str:
        return self._device

    def get_available_devices(self) -> dict:
        from utils.utils import get_device_map
        return get_device_map()

    def get_server_variables(self) -> list[dict]:
        return [
            {"key": "whisper_model", "label": "Model", "value": self._model_name},
            {"key": "device", "label": "Device", "value": self._device}
        ]

    def _build_model(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return whisper.load_model(self._model_name, device=self._device)

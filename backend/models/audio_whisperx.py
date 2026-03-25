import gc
import json
import logging
import os
import warnings

import pysubs2
import whisperx

from interface import AudioModelInterface

# Suppress verbose output from whisperx and its dependencies
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")
warnings.filterwarnings("ignore", category=UserWarning, module="torchcodec")
logging.getLogger("whisperx").setLevel(logging.WARNING)
logging.getLogger("pyannote").setLevel(logging.WARNING)


class AudioWhisperX(AudioModelInterface):
    CONFIG_FILE = "audio_whisperx.json"

    def __init__(self):
        self._model_name = "medium"
        self._device = "cpu"
        self._compute_type = "float32"
        self._batch_size = 16
        self._model = None
        self._running = False
        self._status = "not_loaded"

        _data_path = self._get_config_path(self.CONFIG_FILE)
        if os.path.isfile(_data_path):
            with open(_data_path, "r", encoding="utf-8") as _f:
                _cfg = json.load(_f)
            self._model_name = _cfg.get("model_name", self._model_name)
            self._device = _cfg.get("device", self._device)
            self._compute_type = _cfg.get("compute_type", self._compute_type)
            self._batch_size = _cfg.get("batch_size", self._batch_size)
        else:
            os.makedirs(os.path.dirname(_data_path), exist_ok=True)
            self._save_config()

    def _save_config(self):
        _data_path = self._get_config_path(self.CONFIG_FILE)
        os.makedirs(os.path.dirname(_data_path), exist_ok=True)
        with open(_data_path, "w", encoding="utf-8") as _f:
            json.dump({
                "model_name": self._model_name,
                "device": self._device,
                "compute_type": self._compute_type,
                "batch_size": self._batch_size
            }, _f, indent=2)

    def configure(self, settings: dict):
        if not settings:
            return
        if "model_name" in settings:
            self._model_name = settings["model_name"]
        if "device" in settings:
            self._device = settings["device"]
        if "compute_type" in settings:
            self._compute_type = settings["compute_type"]
        if "batch_size" in settings:
            self._batch_size = int(settings["batch_size"])
        self._save_config()

    def get_settings_schema(self) -> dict:
        return {
            "provider": "audio_whisperx",
            "title": "WhisperX",
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
                        {"label": "large-v2", "value": "large-v2"},
                        {"label": "turbo", "value": "turbo"},
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
                },
                {
                    "key": "compute_type",
                    "label": "Compute Type",
                    "type": "select",
                    "options": [
                        {"label": "float32", "value": "float32"},
                        {"label": "float16", "value": "float16"},
                        {"label": "int8", "value": "int8"},
                    ],
                    "default": self._compute_type,
                    "help": "float16/int8 require CUDA GPU"
                },
                {
                    "key": "batch_size",
                    "label": "Batch Size",
                    "type": "number",
                    "default": self._batch_size,
                    "min": 1,
                    "max": 32,
                    "step": 1,
                    "help": "Reduce if running out of memory"
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

    def transcribe_line(self, audio_path: str, language: str) -> str:
        if not os.path.isfile(audio_path):
            return "File not detected. Did you put the right path?"
        model = self._model or self._build_model()
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, language=language, batch_size=self._batch_size)

        segments = result.get("segments", [])
        if not segments:
            return ""
        return segments[0]["text"].strip()

    def transcribe_file(self, audio_path: str, language: str) -> pysubs2.SSAFile:
        if not os.path.isfile(audio_path):
            return "File not detected. Did you put the right path?"
        model = self._model or self._build_model()

        device = "cuda" if self._device.startswith("cuda") else self._device
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, language=language, batch_size=self._batch_size, chunk_size=10)

        # Align for accurate word-level timestamps
        model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device)

        del model_a
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        subs = pysubs2.SSAFile()
        style = subs.styles["Default"]
        style.fontsize = 55
        style.fontname = "Arial"
        subs.styles["Default"] = style

        for seg in result["segments"]:
            words = seg.get("words", [])
            first_word = next((w for w in words if "start" in w), None)
            last_word = next((w for w in reversed(words) if "end" in w), None)
            start_time = (first_word["start"] if first_word else seg["start"]) * 1000
            end_time = (last_word["end"] if last_word else seg["end"]) * 1000

            print(f"Segment: start={start_time}ms, end={end_time}ms, text='{seg['text'].strip()}'")

            line = pysubs2.SSAEvent(
                start=start_time,
                end=end_time,
                text=seg["text"].strip()
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
            {"key": "whisperx_model", "label": "Model", "value": self._model_name},
            {"key": "device", "label": "Device", "value": self._device},
            {"key": "compute_type", "label": "Compute Type", "value": self._compute_type},
        ]

    def _build_model(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        # ctranslate2 only accepts "cuda" or "cpu", not "cuda:0"
        device = "cuda" if self._device.startswith("cuda") else self._device
        return whisperx.load_model(self._model_name, device, compute_type=self._compute_type)

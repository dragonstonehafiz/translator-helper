import os
import tempfile
import time
from typing import Optional

from models.llm_chatgpt import LLMChatGPT
# from models.llm_llamacpp import LLMLlamaCpp
from models.audio_whisper import AudioWhisper
from interface import LLMInterface, AudioModelInterface
from utils.translate_subs import translate_subs
from utils.logger import setup_logger

logger = setup_logger()


class ModelManager:
    def __init__(self):
        self.audio_client: AudioModelInterface = None
        self.llm_client: LLMInterface = None
        self.loading_audio_model = False
        self.loading_llm_model = False

        self.context_result = None
        self.translation_result = None
        self.transcription_result = None
        self.translation_progress = {
            "current": 0,
            "total": 0,
            "avg_seconds_per_line": 0.0,
            "eta_seconds": 0.0
        }
        self.transcription_elapsed = None
        self.translation_elapsed = None
        self.translation_start_time = None
        self.last_line_translation_input = None
        self.last_line_translation_output = None
        self.last_line_translation_elapsed = None

        self.llm_error = None
        self.transcription_error = None

    def is_llm_running(self) -> bool:
        return bool(self.llm_client and self.llm_client.is_running())

    def is_audio_running(self) -> bool:
        return bool(self.audio_client and self.audio_client.is_running())

    def is_llm_ready(self) -> bool:
        return bool(self.llm_client and self.llm_client.get_status() == "loaded")

    def is_audio_ready(self) -> bool:
        return bool(self.audio_client and self.audio_client.get_status() == "loaded")

    def _update_translation_progress(self, current: int, total: int):
        avg_seconds = 0.0
        eta_seconds = 0.0
        if self.translation_start_time and current > 0:
            elapsed = time.time() - self.translation_start_time
            avg_seconds = elapsed / current
            if total > current:
                eta_seconds = avg_seconds * (total - current)

        self.translation_progress = {
            "current": current,
            "total": total,
            "avg_seconds_per_line": avg_seconds,
            "eta_seconds": eta_seconds
        }

    def load_audio_model(self):
        if self.loading_audio_model:
            return False
        try:
            self.loading_audio_model = True
            if self.audio_client is None:
                self.audio_client = AudioWhisper()
            else:
                pass
            self.audio_client.initialize()
            logger.info(f"Whisper model loaded: model='{self.audio_client.get_model()}', device='{self.audio_client.get_device()}'")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            print(f"Error loading Whisper model: {e}")
        finally:
            self.loading_audio_model = False

        return True

    def apply_audio_settings(self, settings: dict):
        if self.audio_client is None:
            raise RuntimeError("Audio model is not initialized.")
        if settings:
            self.audio_client.configure(settings)

    def load_llm_model(self):
        if self.loading_llm_model:
            return False
        try:
            self.loading_llm_model = True
            if self.llm_client is None:
                self.llm_client = LLMChatGPT()
            else:
                pass
            self.llm_client.initialize()
            logger.info(f"LLM loaded: model='{self.llm_client.get_model()}', temperature={self.llm_client.get_temperature()}")
        except Exception as e:
            logger.error(f"Error loading LLM model: {e}")
            print(f"Error loading LLM model: {e}")
        finally:
            self.loading_llm_model = False

        return True

    def apply_llm_settings(self, settings: dict):
        if self.llm_client is None:
            raise RuntimeError("LLM model is not initialized.")
        if settings:
            self.llm_client.configure(settings)

    def run_transcription_task(self, file_path: str, language: str):
        start_time = time.time()
        try:
            if self.audio_client:
                self.audio_client.set_running(True)
            self.transcription_result = None
            self.transcription_error = None
            logger.info(f"Starting audio transcription: file='{file_path}', language='{language}'")

            result = self.audio_client.transcribe_line(file_path, language)
            self.transcription_result = {"type": "transcription", "data": result}
            logger.info("Successfully completed audio transcription")
            self.transcription_elapsed = time.time() - start_time
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            print(f"Error transcribing audio: {e}")
            self.transcription_error = str(e)
            self.transcription_elapsed = time.time() - start_time
        finally:
            if self.audio_client:
                self.audio_client.set_running(False)
            logger.info("Audio transcription process completed")
            try:
                os.remove(file_path)
            except:
                pass

    def run_translate_file_task(self, file_path: str, context: dict, input_lang: str, output_lang: str, batch_size: int):
        try:
            if self.llm_client:
                self.llm_client.set_running(True)
            self.translation_result = None
            self.llm_error = None
            logger.info(f"Starting file translation: file='{file_path}', input_lang='{input_lang}', output_lang='{output_lang}'")

            import pysubs2
            subs = pysubs2.load(file_path)

            import time
            start_time = time.time()
            self.translation_start_time = time.time()
            self.translation_progress = {
                "current": 0,
                "total": len(subs),
                "avg_seconds_per_line": 0.0,
                "eta_seconds": 0.0
            }
            translated_subs = translate_subs(
                llm=self.llm_client,
                subs=subs,
                context=context if context else {},
                batch_size=batch_size,
                input_lang=input_lang,
                target_lang=output_lang,
                temperature=self.llm_client.get_temperature(),
                progress_callback=self._update_translation_progress
            )
            elapsed_seconds = time.time() - start_time
            logger.info("File translation completed in %.2fs", elapsed_seconds)
            self.translation_elapsed = elapsed_seconds

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=os.path.splitext(file_path)[1], encoding='utf-8') as tmp_file:
                translated_subs.save(tmp_file.name)
                output_path = tmp_file.name

            with open(output_path, 'r', encoding='utf-8') as f:
                output_content = f.read()

            original_filename = os.path.basename(file_path)
            name, ext = os.path.splitext(original_filename)
            translated_filename = f"{name}_translated{ext}"

            self.translation_result = {
                "type": "file_translation",
                "data": output_content,
                "filename": translated_filename
            }
            self.translation_progress = {
                "current": self.translation_progress["total"],
                "total": self.translation_progress["total"],
                "avg_seconds_per_line": self.translation_progress["avg_seconds_per_line"],
                "eta_seconds": 0.0
            }

            try:
                os.remove(output_path)
            except:
                pass
        except Exception as e:
            logger.error(f"Error translating file: {e}")
            print(f"Error translating file: {e}")
            self.llm_error = str(e)
            self.translation_elapsed = None
        finally:
            if self.llm_client:
                self.llm_client.set_running(False)
            try:
                os.remove(file_path)
            except:
                pass
            self.translation_progress = {
                "current": 0,
                "total": 0,
                "avg_seconds_per_line": 0.0,
                "eta_seconds": 0.0
            }
            self.translation_start_time = None

    def run_llm_task(
        self,
        prompt: str,
        system_prompt: str | None,
        result_type: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        target: str = "context",
        cleanup_path: str | None = None
    ):
        start_time = time.time()
        try:
            if self.llm_client:
                self.llm_client.set_running(True)
            self.llm_error = None

            if target == "context":
                self.context_result = None
            else:
                self.translation_result = None

            result = self.llm_client.infer(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            payload = {"type": result_type, "data": result}
            if target == "context":
                self.context_result = payload
                elapsed_seconds = time.time() - start_time
                logger.info("Context task '%s' completed in %.2fs", result_type, elapsed_seconds)
            else:
                self.translation_result = payload
                self.translation_elapsed = time.time() - start_time
                if result_type == "line_translation":
                    self.last_line_translation_input = prompt
                    self.last_line_translation_output = result
                    self.last_line_translation_elapsed = self.translation_elapsed
                    logger.info(
                        'Line translation: input="%s", output="%s", inference_time="%.2fs"',
                        prompt,
                        result,
                        self.translation_elapsed
                    )
        except Exception as e:
            logger.error(f"Error running LLM task ({result_type}): {e}")
            print(f"Error running LLM task ({result_type}): {e}")
            self.llm_error = str(e)
            if target != "context":
                self.translation_elapsed = None
        finally:
            if self.llm_client:
                self.llm_client.set_running(False)
            if cleanup_path:
                try:
                    os.remove(cleanup_path)
                except:
                    pass

import os
import tempfile
from typing import Optional

from models.llm_chatgpt import LLMChatGPT, LLMInterface
from models.audio_whisper import AudioWhisper, AudioModelInterface
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
            self.audio_client = AudioWhisper()
        if settings:
            self.audio_client.configure(settings)

    def reload_audio_model(self):
        if self.loading_audio_model:
            return False
        try:
            self.loading_audio_model = True
            if self.audio_client is None:
                self.audio_client = AudioWhisper()
            self.audio_client.initialize()
            logger.info(f"Whisper model loaded: model='{self.audio_client.get_model()}', device='{self.audio_client.get_device()}'")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            print(f"Error loading Whisper model: {e}")
        finally:
            self.loading_audio_model = False
        return True

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
            logger.error(f"Error loading GPT model: {e}")
            print(f"Error loading GPT model: {e}")
        finally:
            self.loading_llm_model = False

        return True

    def apply_llm_settings(self, settings: dict):
        if self.llm_client is None:
            self.llm_client = LLMChatGPT()
        if settings:
            self.llm_client.configure(settings)

    def reload_llm_model(self):
        if self.loading_llm_model:
            return False
        try:
            self.loading_llm_model = True
            if self.llm_client is None:
                self.llm_client = LLMChatGPT()
            self.llm_client.initialize()
            logger.info(f"LLM loaded: model='{self.llm_client.get_model()}', temperature={self.llm_client.get_temperature()}")
        except Exception as e:
            logger.error(f"Error loading GPT model: {e}")
            print(f"Error loading GPT model: {e}")
        finally:
            self.loading_llm_model = False
        return True

    def run_transcription_task(self, file_path: str, language: str):
        try:
            if self.audio_client:
                self.audio_client.set_running(True)
            self.transcription_result = None
            self.transcription_error = None
            logger.info(f"Starting audio transcription: file='{file_path}', language='{language}'")

            result = self.audio_client.transcribe_line(file_path, language)
            self.transcription_result = {"type": "transcription", "data": result}
            logger.info("Successfully completed audio transcription")
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            print(f"Error transcribing audio: {e}")
            self.transcription_error = str(e)
        finally:
            if self.audio_client:
                self.audio_client.set_running(False)
            logger.info("Audio transcription process completed")
            try:
                os.remove(file_path)
            except:
                pass

    def run_translate_file_task(self, file_path: str, context: dict, input_lang: str, output_lang: str, context_window: int):
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
            translated_subs = translate_subs(
                llm=self.llm_client,
                subs=subs,
                context=context if context else {},
                context_window=context_window,
                input_lang=input_lang,
                target_lang=output_lang,
                temperature=self.llm_client.get_temperature()
            )
            elapsed_seconds = time.time() - start_time
            logger.info("File translation completed in %.2fs", elapsed_seconds)

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

            try:
                os.remove(output_path)
            except:
                pass
        except Exception as e:
            logger.error(f"Error translating file: {e}")
            print(f"Error translating file: {e}")
            self.llm_error = str(e)
        finally:
            if self.llm_client:
                self.llm_client.set_running(False)
            logger.info("File translation process completed")
            try:
                os.remove(file_path)
            except:
                pass

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
            else:
                self.translation_result = payload
        except Exception as e:
            logger.error(f"Error running LLM task ({result_type}): {e}")
            print(f"Error running LLM task ({result_type}): {e}")
            self.llm_error = str(e)
        finally:
            if self.llm_client:
                self.llm_client.set_running(False)
            if cleanup_path:
                try:
                    os.remove(cleanup_path)
                except:
                    pass

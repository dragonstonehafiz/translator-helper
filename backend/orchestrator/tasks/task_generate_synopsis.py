import os
import time

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.result_handler import ResultHandler
from utils.logger import setup_logger
from prompts.context import generate_synopsis_prompt
from utils.utils import load_sub_data

logger = setup_logger("task-timings")


class TaskGenerateSynopsis(BaseTask):
    TASK_TYPE = "TaskGenerateSynopsis"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        started = time.perf_counter()
        status = "error"
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            return {}

        data = self.get_data()
        file_path = str(data.get("file_path", ""))
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))

        result_handler.set_processing(self.task_type)
        try:
            llm_client.set_running(True)
            transcript = "\n".join(load_sub_data(file_path, include_speaker=True))
            system_prompt = generate_synopsis_prompt(
                context=context if context else None,
                input_lang=input_lang,
                output_lang=output_lang,
            )
            output = model_manager.llm_infer(prompt=transcript, system_prompt=system_prompt)
            payload = {"text": output}
            result_handler.set_complete(self.task_type, payload)
            status = "complete"
            return payload
        except Exception as exc:
            logger.error("Error generating synopsis: %s", exc, exc_info=True)
            result_handler.set_error(self.task_type, str(exc))
            return {}
        finally:
            llm_client.set_running(False)
            if file_path:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            logger.info("task=%s status=%s elapsed_seconds=%.3f", self.task_type, status, time.perf_counter() - started)

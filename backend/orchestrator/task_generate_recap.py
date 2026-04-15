import time

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.result_handler import ResultHandler
from utils.logger import setup_logger
from prompts.recap import generate_recap_prompt

logger = setup_logger("task-timings")


class TaskGenerateRecap(BaseTask):
    TASK_TYPE = "TaskGenerateRecap"

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
        contexts = data.get("contexts") or []
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))

        all_keys = set()
        for ctx in contexts:
            all_keys.update(ctx.keys())
        metadata_keys = {"seriesName", "keywords", "inputLanguage", "outputLanguage", "exportDate"}
        all_keys = all_keys - metadata_keys

        sections_data = {}
        for key in all_keys:
            values = []
            for i, ctx in enumerate(contexts):
                value = ctx.get(key, "")
                if value and str(value).strip():
                    values.append((i, str(value).strip()))
            if values:
                sections_data[key] = values

        if not sections_data:
            all_context = ""
        else:
            context_sections = []
            for key, values in sections_data.items():
                title = key.replace("_", " ").title()
                combined = "\n\n".join([f"### Part {i + 1}\n{val}" for i, val in values])
                context_sections.append(f"## {title}\n\n{combined}")
            all_context = "\n\n".join(context_sections)

        result_handler.set_processing(self.task_type)
        try:
            llm_client.set_running(True)
            system_prompt = generate_recap_prompt(
                all_context=all_context,
                input_lang=input_lang,
                output_lang=output_lang,
            )
            output = model_manager.llm_infer(prompt="Generate recap.", system_prompt=system_prompt)
            payload = {"type": "recap", "data": output}
            result_handler.set_complete(self.task_type, payload)
            status = "complete"
            return payload
        except Exception as exc:
            logger.error("Error generating recap: %s", exc, exc_info=True)
            result_handler.set_error(self.task_type, str(exc))
            return {}
        finally:
            llm_client.set_running(False)
            logger.info("task=%s status=%s elapsed_seconds=%.3f", self.task_type, status, time.perf_counter() - started)

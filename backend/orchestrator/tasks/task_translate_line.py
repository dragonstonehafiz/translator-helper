from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.result_handler import ResultHandler
from prompts.translate import generate_translate_sub_prompt


class TaskTranslateLine(BaseTask):
    """Standalone task: translate a single subtitle line from input_lang to output_lang using the LLM."""

    TASK_TYPE = "TaskTranslateLine"

    @property
    def task_type(self) -> str:
        """Return the task type identifier."""
        return self.TASK_TYPE

    def run_task(self) -> dict:
        """Translate data['text'] and return a result dict with the translated text; final task so it stores a complete result."""
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()

        data = self.get_data()
        text = str(data.get("text", ""))
        context = data.get("context") or {}
        input_lang = str(data.get("input_lang", "ja"))
        output_lang = str(data.get("output_lang", "en"))

        result_handler.set_processing(self.task_type)
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            raise RuntimeError("LLM model not initialized")

        system_prompt = generate_translate_sub_prompt(
            context=context,
            input_lang=input_lang,
            target_lang=output_lang,
        )

        try:
            llm_client.set_running(True)
            translated_text = model_manager.llm_infer(
                prompt=text,
                system_prompt=system_prompt,
            )
            payload = {"text": translated_text}
            result_handler.set_complete(self.task_type, payload)
            return payload
        except Exception as exc:
            result_handler.set_error(self.task_type, str(exc))
            raise
        finally:
            llm_client.set_running(False)

from models.manager import ModelManager
from orchestrator.base_task import BaseTask, ReportProgress, WriteLog
from orchestrator.task_data.base import TextOutputData
from orchestrator.task_data.general import TranslateLineData
from prompts.translate import generate_translate_sub_prompt


class TaskTranslateLine(BaseTask[TranslateLineData, TextOutputData]):
    """Translate a single subtitle line from input_lang to output_lang using the LLM."""

    input_type = TranslateLineData
    output_type = TextOutputData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> TextOutputData:
        """Translate the line and return the translated text."""
        data = self.get_data()
        model_manager = ModelManager.get_instance()
        llm = model_manager.get_llm_client()
        report_progress(0, 1, "Translating the entered text", 0.0)
        translated_text = llm.infer(
            prompt=data.text,
            system_prompt=generate_translate_sub_prompt(
                context=data.context,
                input_lang=data.input_lang,
                target_lang=data.output_lang,
            ),
        )
        report_progress(1, 1, "Translation complete", 0.0)
        return TextOutputData(text=translated_text)

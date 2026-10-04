from orchestrator.task_data.base import TaskData
from orchestrator.task_data.general import TranslateLineData
from orchestrator.task_orchestrator import TaskOrchestrator
from orchestrator.tasks.task_translate_line import TaskTranslateLine
from orchestrator.workflows import no_cleanup

WORKFLOW = "translate_line"


def start_translate_line(text: str, context: dict[str, str], input_lang: str, output_lang: str) -> None:
    """Start translating one line; the result is TextOutputData."""
    data = TranslateLineData(text=text, context=context, input_lang=input_lang, output_lang=output_lang)
    TaskOrchestrator.get_instance().run(WORKFLOW, [TaskTranslateLine()], data, finish=_finish, cleanup=no_cleanup)


def _finish(data: TaskData) -> TaskData:
    """The translated text is already the final result."""
    return data

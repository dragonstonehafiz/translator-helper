# Run from backend/:
# python tests\run_plan_translation_batches.py --file-path ..\data\sample\sample_sub_gakumas_tokimeki.ass --input-lang ja --output-lang en --batch-size 50 --pretty

import argparse
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _parse_args() -> argparse.Namespace:
    """Parse the harness command-line options."""
    parser = argparse.ArgumentParser(
        description="Run the translation batch preparation task (planning plus oversized-batch splitting) in isolation."
    )
    parser.add_argument("--file-path", required=True, help="Path to the subtitle file to analyze.")
    parser.add_argument("--input-lang", default="ja", help="Source language code or label passed to the planner prompt.")
    parser.add_argument("--output-lang", default="en", help="Target language code or label passed to the planner prompt.")
    parser.add_argument("--batch-size", type=int, default=50, help="Maximum allowed batch size for the final repaired plan.")
    parser.add_argument("--context-json", default="{}", help="Inline JSON object for planner context.")
    parser.add_argument("--context-file", help="Path to a JSON file containing planner context.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON result.")
    return parser.parse_args()


def _load_context(args: argparse.Namespace) -> dict:
    """Read planner context from --context-file or --context-json."""
    if args.context_file:
        return json.loads(Path(args.context_file).read_text(encoding="utf-8"))
    return json.loads(args.context_json)


def _make_temp_copy(file_path: Path) -> Path:
    """Copy the input to a temp file so the run's cleanup never deletes the user's file."""
    suffix = file_path.suffix or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        temp_path = Path(tmp_file.name)
    shutil.copyfile(file_path, temp_path)
    return temp_path


def main() -> int:
    """Load the LLM, run batch preparation through the orchestrator and print the resulting plan."""
    args = _parse_args()

    try:
        from models.manager import ModelManager
        from orchestrator.task_data.base import TaskData
        from orchestrator.task_data.translation import PlannedTranslationData, TranslationBatch, TranslationData
        from orchestrator.task_orchestrator import TaskOrchestrator
        from orchestrator.translate_file.task_prepare_translation_batches import TaskPrepareTranslationBatches
        from orchestrator.workflows import remove_files
        from utils.subtitles import load_subtitles
    except Exception as exc:
        print(json.dumps({"status": "error", "message": f"Failed to import backend task dependencies: {exc}"}))
        return 1

    @dataclass(kw_only=True)
    class PlanResultData(TaskData):
        """Compact plan printed by the harness."""

        batches: list[TranslationBatch]

    def finish(data: TaskData) -> PlanResultData:
        """Keep only the final batch plan."""
        if not isinstance(data, PlannedTranslationData):
            raise TypeError(f"Expected PlannedTranslationData, got {type(data).__name__}.")
        return PlanResultData(batches=data.batches)

    model_manager = ModelManager.get_instance()
    try:
        model_manager.load_llm_model()
    except Exception as exc:
        print(json.dumps({"status": "error", "message": f"LLM model not loaded: {exc}"}))
        return 1
    print(f"Loaded LLM provider: {model_manager.get_llm_client().provider_id}")

    source_file = Path(args.file_path).expanduser().resolve()
    if not source_file.is_file():
        print(json.dumps({"status": "error", "message": f"File not found: {source_file}"}))
        return 1
    try:
        context = _load_context(args)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": f"Invalid context input: {exc}"}))
        return 1

    temp_file_path = _make_temp_copy(source_file)
    task_orchestrator = TaskOrchestrator.get_instance()
    try:
        data = TranslationData(
            original_filename=source_file.name,
            subtitles=load_subtitles(str(temp_file_path)),
            input_lang=args.input_lang,
            output_lang=args.output_lang,
            batch_size=max(1, args.batch_size),
            context=context,
            series=None,
            library_context=None,
        )
        task_orchestrator.run(
            "translate_file",
            [TaskPrepareTranslationBatches()],
            data,
            finish=finish,
            cleanup=remove_files(temp_file_path),
        )
    except Exception as exc:
        temp_file_path.unlink(missing_ok=True)
        print(json.dumps({"status": "error", "message": str(exc)}))
        return 1

    task_orchestrator.shutdown()
    model_manager.shutdown()
    state = task_orchestrator.get_state_handler().get("translate_file")
    if state is None or state.status != "complete":
        response = {"status": "error", "message": state.error if state else "Run did not start."}
    else:
        response = {"status": "complete", "batches": [batch.to_log() for batch in state.result.batches]}
    print(json.dumps(response, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0 if response["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

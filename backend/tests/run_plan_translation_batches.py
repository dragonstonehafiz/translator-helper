# Run from backend/:
# python tests\run_plan_translation_batches.py --file-path ..\data\sample\sample_sub_gakumas_tokimeki.ass --input-lang ja --output-lang en --batch-size 50 --pretty

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the translation batch planner task in isolation."
    )
    parser.add_argument(
        "--file-path",
        required=True,
        help="Path to the subtitle file to analyze.",
    )
    parser.add_argument(
        "--input-lang",
        default="ja",
        help="Source language code or label passed to the planner prompt.",
    )
    parser.add_argument(
        "--output-lang",
        default="en",
        help="Target language code or label passed to the planner prompt.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Maximum allowed batch size for the final repaired plan.",
    )
    parser.add_argument(
        "--context-json",
        default="{}",
        help="Inline JSON object for planner context.",
    )
    parser.add_argument(
        "--context-file",
        help="Path to a JSON file containing planner context.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON result.",
    )
    return parser.parse_args()


def _load_context(args: argparse.Namespace) -> dict:
    if args.context_file:
        return json.loads(Path(args.context_file).read_text(encoding="utf-8"))
    return json.loads(args.context_json)


def _make_temp_copy(file_path: Path) -> str:
    suffix = file_path.suffix or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        temp_path = Path(tmp_file.name)
    shutil.copyfile(file_path, temp_path)
    return str(temp_path)


def main() -> int:
    args = _parse_args()

    try:
        from models.model_manager import ModelManager
        from orchestrator.task_orchestrator import TaskOrchestrator
        from orchestrator.result_handler import ResultHandler
        from orchestrator.task_plan_translation_batches import TaskPlanTranslationBatches
        from orchestrator.task_split_oversized_batches import TaskSplitOversizedBatches
    except Exception as exc:
        print(json.dumps({"status": "error", "message": f"Failed to import backend task dependencies: {exc}"}))
        return 1

    model_manager = ModelManager.get_instance()
    if not model_manager.is_llm_ready():
        message = model_manager.llm_loading_error or "LLM model not loaded."
        print(json.dumps({"status": "error", "message": message}))
        return 1
    llm_client = model_manager.get_llm_client()
    loaded_model = llm_client.get_model() if llm_client is not None else "unknown"
    print(f"Loaded LLM model: {loaded_model}")

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
    semantic_task = TaskPlanTranslationBatches()
    split_task = TaskSplitOversizedBatches()
    initial_data = {
        "file_path": temp_file_path,
        "original_filename": source_file.name,
        "context": context,
        "input_lang": args.input_lang,
        "output_lang": args.output_lang,
        "batch_size": args.batch_size,
    }

    task_orchestrator.clear_tasks()
    task_orchestrator.add_task(semantic_task)
    task_orchestrator.add_task(split_task)
    try:
        payload = task_orchestrator.run_tasks(initial_data=initial_data)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return 1

    semantic_record = ResultHandler.get_instance().get(semantic_task.task_type)
    final_record = ResultHandler.get_instance().get(split_task.task_type)
    semantic_result = semantic_record.get("result") if semantic_record and semantic_record.get("status") == "complete" else None

    if semantic_record and semantic_record.get("status") == "error":
        response = {
            "status": "error",
            "task_type": semantic_task.task_type,
            "result": None,
            "message": semantic_record.get("error"),
        }
        if args.pretty:
            print(json.dumps(response, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(response, ensure_ascii=False))
        return 1

    if semantic_result and semantic_result.get("batches"):
        oversized_batches = []
        for batch in semantic_result["batches"]:
            start_index = int(batch["start_index"])
            end_index = int(batch["end_index"])
            size = end_index - start_index + 1
            if size > args.batch_size:
                oversized_batches.append({
                    "start_index": start_index,
                    "end_index": end_index,
                    "size": size,
                    "max_batch_size": args.batch_size,
                    "reason": batch["reason"],
                })
    else:
        oversized_batches = []

    if oversized_batches:
        print("Oversized batches requiring correction:")
        for batch in oversized_batches:
            print(
                f"- {batch['start_index']}-{batch['end_index']} "
                f"(size {batch['size']}, max {batch['max_batch_size']}): {batch['reason']}"
            )

    response = {
        "status": "complete" if payload else "error",
        "task_type": split_task.task_type,
        "result": payload if payload else None,
    }
    if final_record and final_record.get("status") == "error":
        response["status"] = "error"
        response["message"] = final_record.get("error")

    if args.pretty:
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(response, ensure_ascii=False))
    return 0 if response["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

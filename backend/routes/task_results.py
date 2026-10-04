"""
Workflow polling route.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from orchestrator.task_data.base import FileOutputData, ReviewFileOutputData, TaskData, TextOutputData
from orchestrator.task_data.library_update import ProposalOutputData
from orchestrator.task_orchestrator import WORKFLOWS, TaskOrchestrator
from utils.api_response import complete_response, error_response, idle_response, processing_response

router = APIRouter(prefix="/task-results")


def _public_result(result: TaskData | None) -> dict[str, Any] | None:
    """Turn a workflow's final data into its public shape; never exposes paths or subtitle objects."""
    if result is None:
        return None
    if isinstance(result, TextOutputData):
        return {"text": result.text}
    if isinstance(result, ReviewFileOutputData):
        return {"output_filename": result.output_path.name, "folder": result.output_path.parent.name, "corrected_count": result.corrected_count}
    if isinstance(result, FileOutputData):
        return {"output_filename": result.output_path.name, "folder": result.output_path.parent.name}
    if isinstance(result, ProposalOutputData):
        return {"proposals": result.proposals}
    raise TypeError(f"No public result shape for {type(result).__name__}.")


@router.get("/{workflow}")
async def get_workflow_result(workflow: str):
    """Return one consistent snapshot of a workflow's state; idle if it has not run since the server started."""
    if workflow not in WORKFLOWS:
        raise HTTPException(status_code=400, detail="Invalid workflow")

    state = TaskOrchestrator.get_instance().get_state_handler().get(workflow)
    if state is None:
        return idle_response({"workflow": workflow})

    data = {
        "workflow": state.workflow,
        "active_task": state.active_task,
        "progress": list(state.progress),
        "message": state.message,
        "eta_seconds": state.eta_seconds,
        "result": _public_result(state.result) if state.status == "complete" else None,
    }
    if state.status == "complete":
        return complete_response(data)
    if state.status == "error":
        return error_response(state.error or "Workflow failed.", data)
    return processing_response(data)

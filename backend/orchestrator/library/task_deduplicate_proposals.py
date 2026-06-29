import json
from pathlib import Path

from interface.base_task import BaseTask
from models.model_manager import ModelManager
from orchestrator.progress_handler import ProgressHandler
from orchestrator.result_handler import ResultHandler
from prompts.library import deduplicate_proposals_prompt
from utils.logger import setup_logger

logger = setup_logger("translator-helper")


class TaskDeduplicateProposals(BaseTask):
    TASK_TYPE = "TaskDeduplicateProposals"

    @property
    def task_type(self) -> str:
        return self.TASK_TYPE

    def run_task(self) -> dict:
        model_manager = ModelManager.get_instance()
        result_handler = ResultHandler.get_instance()
        progress_handler = ProgressHandler.get_instance()
        llm_client = model_manager.get_llm_client()
        if llm_client is None:
            result_handler.set_error(self.task_type, "LLM model not initialized")
            raise RuntimeError("LLM model not initialized")

        data = self.get_data()
        proposals = data.get("proposals", {})
        series = data.get("series", {})

        log_dir = data.get("log_dir")
        updated = proposals.get("updated_characters", [])
        if not updated:
            result_handler.set_complete(self.task_type, {"proposals": proposals})
            self._write_log(log_dir, proposals, proposals)
            return data

        result_handler.set_processing(self.task_type)

        # Build dedup groups:
        # personality → { char_id: [appends] }
        # history     → { char_id: [appends] }
        # relationships → { relationship_character_name: [(char_id, append)] }
        personality_groups: dict[str, list] = {}
        history_groups: dict[str, list] = {}
        relationship_groups: dict[str, list] = {}

        for u in updated:
            char_id = u.get("id", "")
            field = u.get("field", "")
            append = u.get("append", "")
            if field == "personality":
                personality_groups.setdefault(char_id, []).append(u)
            elif field == "history":
                history_groups.setdefault(char_id, []).append(u)
            elif field == "relationships":
                rel_char = u.get("character", "")
                relationship_groups.setdefault(rel_char, []).append(u)

        char_map = {c["id"]: c for c in series.get("characters", [])}
        kept: list[dict] = []
        # Stores existing library data per group key for the audit log
        existing_by_group: dict[str, list[str]] = {}

        total_calls = len(personality_groups) + len(history_groups) + len(relationship_groups)
        completed = 0
        progress_handler.set(self.task_type, {"current": 0, "total": total_calls, "status": "Deduplicating proposals", "eta_seconds": 0})

        try:
            llm_client.set_running(True)

            # Personality — one call per character
            for char_id, proposals_list in personality_groups.items():
                char = char_map.get(char_id, {})
                existing = char.get("personality", [])
                existing_by_group[f"{char_id} | personality"] = existing
                kept_indices = self._dedup_call(model_manager, "personality", existing, proposals_list, label_key="append")
                kept.extend(proposals_list[i] for i in kept_indices)
                completed += 1
                progress_handler.set(self.task_type, {"current": completed, "total": total_calls, "status": f"Checked personality for {char.get('name', char_id)}", "eta_seconds": 0})

            # History — one call per character
            for char_id, proposals_list in history_groups.items():
                char = char_map.get(char_id, {})
                existing = char.get("history", [])
                existing_by_group[f"{char_id} | history"] = existing
                kept_indices = self._dedup_call(model_manager, "history", existing, proposals_list, label_key="append")
                kept.extend(proposals_list[i] for i in kept_indices)
                completed += 1
                progress_handler.set(self.task_type, {"current": completed, "total": total_calls, "status": f"Checked history for {char.get('name', char_id)}", "eta_seconds": 0})

            # Relationships — one call per relationship character name
            for rel_char, proposals_list in relationship_groups.items():
                existing = []
                for char in series.get("characters", []):
                    facts = char.get("relationships", {}).get(rel_char, [])
                    existing.extend(facts)
                existing_by_group[f"relationships | {rel_char}"] = existing
                kept_indices = self._dedup_call(model_manager, f"relationships[{rel_char}]", existing, proposals_list, label_key="append")
                kept.extend(proposals_list[i] for i in kept_indices)
                completed += 1
                progress_handler.set(self.task_type, {"current": completed, "total": total_calls, "status": f"Checked relationship: {rel_char}", "eta_seconds": 0})

        finally:
            llm_client.set_running(False)

        deduped_proposals = {**proposals, "updated_characters": kept}
        progress_handler.set(self.task_type, {"current": total_calls, "total": total_calls, "status": f"Kept {len(kept)}/{len(updated)} updated_characters proposals", "eta_seconds": 0})
        result_handler.set_complete(self.task_type, {"proposals": deduped_proposals})
        self._write_log(log_dir, proposals, deduped_proposals, existing_by_group)
        return {**data, "proposals": deduped_proposals}

    def _write_log(self, log_dir, original_proposals: dict, deduped_proposals: dict, existing_by_group: dict):
        """Write a per-group audit log showing existing library data, proposed additions, kept, and excluded entries."""
        if not log_dir:
            return
        log_path = Path(log_dir) / "06-deduplicate-proposals.json"
        original_updated = original_proposals.get("updated_characters", [])
        deduped_updated = deduped_proposals.get("updated_characters", [])
        deduped_set = {(u.get("id"), u.get("field"), u.get("character",""), u.get("append","")) for u in deduped_updated}

        groups: dict[str, dict] = {}
        for u in original_updated:
            key = f"{u.get('id')} | {u.get('field')}" + (f" | {u['character']}" if "character" in u else "")
            if key not in groups:
                existing_key = f"{u.get('id')} | {u.get('field')}" if "character" not in u else f"relationships | {u['character']}"
                groups[key] = {
                    "existing_in_library": existing_by_group.get(existing_key, []),
                    "proposed": [],
                    "kept": [],
                    "excluded": [],
                }
            bucket = "kept" if (u.get("id"), u.get("field"), u.get("character",""), u.get("append","")) in deduped_set else "excluded"
            groups[key]["proposed"].append(u.get("append", ""))
            groups[key][bucket].append(u.get("append", ""))

        log_path.write_text(json.dumps({
            "updated_characters_dedup": groups,
            "new_characters": deduped_proposals.get("new_characters", []),
            "new_glossary": deduped_proposals.get("new_glossary", []),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def _dedup_call(self, model_manager, field: str, existing: list, proposals_list: list, label_key: str) -> list[int]:
        existing_text = "\n".join(f"- {e}" for e in existing) if existing else "(none)"
        proposed_lines = "\n".join(f"{i + 1}. {p[label_key]}" for i, p in enumerate(proposals_list))
        prompt = f"=== EXISTING {field.upper()} ENTRIES ===\n{existing_text}\n\n=== PROPOSED ADDITIONS ===\n{proposed_lines}"
        try:
            raw = model_manager.llm_infer(
                prompt=prompt,
                system_prompt=deduplicate_proposals_prompt(field),
                temperature=0.0,
            )
            text = raw.strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                indices = json.loads(text[start:end])
                return [i - 1 for i in indices if isinstance(i, int) and 1 <= i <= len(proposals_list)]
            return list(range(len(proposals_list)))
        except Exception as exc:
            logger.warning("Dedup call failed for field %s: %s — keeping all proposals", field, exc)
            return list(range(len(proposals_list)))

"""
Prompts for selecting relevant library context for translation tasks.
"""


def select_library_context_prompt(
    series_name: str,
    input_lang: str,
    output_lang: str,
    character_ids: list[str],
    character_names: list[str],
    glossary_ids: list[str],
    glossary_terms: list[str],
) -> str:
    """Return a system prompt that asks the LLM to select relevant characters and glossary terms."""
    chars_list = "\n".join(f"- {cid}: {name}" for cid, name in zip(character_ids, character_names)) or "none"
    terms_list = "\n".join(f"- {tid}: {term}" for tid, term in zip(glossary_ids, glossary_terms)) or "none"

    return f"""You are a translation assistant helping to select the most relevant library entries for a subtitle translation task.

You will be given the full subtitle transcript for one episode of "{series_name}" (source: {input_lang}, target: {output_lang}).

From the lists below, select ONLY the characters and glossary terms that actually appear in or are directly relevant to the content of the subtitle transcript. Do not include entries that have no connection to the episode content.

Available characters (id: name):
{chars_list}

Available glossary terms (id: term):
{terms_list}

Respond ONLY with a valid JSON object in this exact format with no markdown, no code fences:
{{
  "character_ids": ["id1", "id2"],
  "glossary_ids": ["id1", "id2"]
}}

If no characters or no glossary terms are relevant, return an empty array for that field."""

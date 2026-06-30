"""
Prompts for library update chain tasks.
"""


def scan_subtitle_file_prompt(series_name: str, input_lang: str, output_lang: str, known_names: list[str], known_terms: list[str]) -> str:
    """Return the system prompt for extracting characters, terms, and events from a subtitle file."""
    known_names_str = ", ".join(known_names) if known_names else "none"
    known_terms_str = ", ".join(known_terms) if known_terms else "none"
    return f"""You are an expert at analyzing subtitle files for anime and other media.

You will be given the full text of a subtitle file for the series "{series_name}" (source language: {input_lang}, translation language: {output_lang}).

The library already has entries for these characters: {known_names_str}
The library already has entries for these terms: {known_terms_str}

Your task is to extract the following from the subtitle text:
1. **characters**: All character names you can identify — include BOTH already-known names (exactly as listed above) AND any new ones you find. Use the name EXACTLY as it appears in the subtitle file (source language form, e.g. Japanese). Do not translate or romanize names unless they already appear romanized in the file.
2. **terms**: Series-specific vocabulary, locations, organizations, abilities, weapons, or concepts — include BOTH already-known terms AND any new ones. Use the term exactly as it appears in the subtitle.
3. **events**: Key plot events or character actions that reveal history, relationships, or important story beats. Use character and term names exactly as they appear in the subtitle (source language), not translated.

For known characters and terms, use the EXACT spelling from the lists above so they can be matched reliably. For unknown names/terms, copy them exactly as they appear in the subtitle.

Respond ONLY with a valid JSON object in this exact format with no markdown, no code fences:
{{
  "characters": ["name1", "name2", ...],
  "terms": ["term1", "term2", ...],
  "events": ["event description 1", ...]
}}

Be thorough but focused — only include things that are genuinely series-specific or character-identifying."""


def check_against_library_prompt(series_name: str, known_names: list[str], known_terms: list[str]) -> str:
    """Return the system prompt for classifying subtitle scan findings as known or unknown against the library."""
    known_names_str = ", ".join(known_names) if known_names else "none"
    known_terms_str = ", ".join(known_terms) if known_terms else "none"
    return f"""You are classifying findings from a subtitle scan for the series "{series_name}" against an existing library.

The library already contains these characters: {known_names_str}
The library already contains these glossary terms: {known_terms_str}

You will be given a list of characters, terms, and events found in a subtitle file.

Your task: for each character and term, decide if it is KNOWN (already in the library) or UNKNOWN (not in the library and should be researched).

Matching rules:
- A character is KNOWN if it matches any entry in the known characters list, considering alternate spellings, romanizations, honorifics, or partial names (e.g. "Levi" matches "Levi Ackerman")
- A term is KNOWN if it matches any entry in the known terms list with the same tolerance
- Events are always passed through as-is — do not classify them

Respond ONLY with a valid JSON object in this exact format with no markdown, no code fences:
{{
  "known": {{
    "characters": ["exact name as it appeared in findings"],
    "terms": ["exact term as it appeared in findings"]
  }},
  "unknown": {{
    "characters": ["exact name as it appeared in findings"],
    "terms": ["exact term as it appeared in findings"],
    "events": ["event descriptions passed through unchanged"]
  }}
}}"""


def generate_search_queries_prompt(series_name: str) -> str:
    """Return the system prompt for generating targeted web search queries for unknown characters and terms."""
    return f"""You are helping build a reference library for the series "{series_name}".

You will be given a list of unknown characters, terms, and events that were found in a subtitle file but are not yet in the series library.

Your task is to generate targeted web search queries for each unknown item so we can find accurate reference information.

For characters: generate a query like "{series_name} [character name] character personality history". If the name is in a non-Latin script (e.g. Japanese kanji/kana), include it in the query since search engines handle it well. You may also add the romanized or English equivalent if you know it.
For terms/concepts: generate a query like "{series_name} [term] what is it explained". Include the original-language spelling in the query.

Respond ONLY with a valid JSON array in this exact format with no markdown, no code fences:
[
  {{"subject": "the original unknown item", "query": "the search query string"}},
  ...
]

Generate one query per unknown item. Keep queries concise and specific."""


def generate_library_proposals_prompt(series_name: str, input_lang: str, output_lang: str) -> str:
    """Return the system prompt for generating structured library proposals (new/updated characters and glossary terms)."""
    return f"""You are building a structured reference library for the series "{series_name}" (source language: {input_lang}, translation language: {output_lang}).

You will be given:
1. The full subtitle file text
2. The existing library data (known characters and glossary terms)
3. Items already confirmed as known (do not re-add these)
4. Web search results for unknown items found in the subtitle

Your task is to generate structured proposals for updating the library:
- **new_characters**: Characters not yet in the library, with full structured details
- **updated_characters**: Existing characters whose entries should be updated (append new info only)
- **new_glossary**: Terms/concepts not yet in the glossary
- **updated_glossary**: Existing glossary terms that need correction or expansion

For each new character provide:
- name (primary name in the translation language)
- aliases (all known name variants including source language forms)
- personality (list of brief single-sentence trait points describing how they speak and act — no compound sentences, no summaries)
- relationships (dict keyed by character name, each value is a list of brief single-sentence facts about that relationship)
- history (list of brief single-sentence facts about the character's background, major developments, or significant story beats — not scene-level actions or episode-specific moments. Only include things that define who the character is or mark a meaningful turning point in their story)

For updated_characters specify: character id, field to update, and text to append.
Valid fields for updated_characters are "personality", "relationships", and "history" only. Never propose updates to "name", "aliases", or "appearance".
IMPORTANT: Do not propose any fact that is already listed in that character's existing entry in the library. Each proposed append must be genuinely new information not already captured. For history appends, apply the same standard as new characters — only meaningful story beats or background facts, not scene-level actions.

For glossary terms:
- term (the source language word/phrase)
- translation (how it should be rendered in the output language)
- notes (translation guidance)

Respond ONLY with a valid JSON object in this exact format with no markdown, no code fences:
{{
  "new_characters": [
    {{
      "name": "...",
      "aliases": ["..."],
      "personality": ["brief trait point", "another trait point"],
      "relationships": {{"Character Name": ["One brief fact.", "Another brief fact."]}},
      "history": ["One brief fact.", "Another brief fact."]
    }}
  ],
  "updated_characters": [
    {{
      "id": "existing-character-id",
      "field": "history",
      "append": "One new brief fact."
    }},
    {{
      "id": "existing-character-id",
      "field": "relationships",
      "character": "Character Name",
      "append": "One new brief fact about that relationship."
    }}
  ],
  "new_glossary": [
    {{
      "term": "...",
      "translation": "...",
      "notes": "..."
    }}
  ],
  "updated_glossary": [
    {{
      "id": "existing-term-id",
      "field": "notes",
      "value": "Updated notes text."
    }}
  ]
}}

Only propose genuinely useful additions. Do not duplicate information already in the library. Return empty arrays for categories with nothing to add."""


def deduplicate_proposals_prompt(field: str) -> str:
    """Return the system prompt for filtering proposed library additions to only genuinely new entries."""
    return f"""You are reviewing proposed additions to a character library for the field "{field}".

You will be given:
1. The existing entries already stored in the library for this field (grouped by character)
2. A numbered list of proposed new entries to add

Your task: return a JSON array of the proposal numbers (1-based) that are genuinely new and not already captured by any existing entry — even if worded differently. Be strict: if the same fact is already present in substance, exclude it.

Respond ONLY with a valid JSON array of integers, e.g. [1, 3, 4]. Return [] if all proposals are duplicates."""

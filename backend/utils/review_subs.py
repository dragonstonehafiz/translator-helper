from interface import LLMInterface
from utils.prompts import PromptGenerator


def review_subs(
    llm: LLMInterface,
    original_subs,
    translated_subs,
    context: dict | None = None,
    input_lang: str = "ja",
    target_lang: str = "en",
    batch_size: int = 3,
    temperature: float | None = None,
    progress_callback=None
):
    if len(original_subs) != len(translated_subs):
        raise ValueError("Original and translated subtitle line counts do not match.")

    prompt_generator = PromptGenerator()
    system_prompt = prompt_generator.generate_review_batch_prompt(
        context=context or {},
        input_lang=input_lang,
        target_lang=target_lang
    )

    total_lines = len(translated_subs)
    batch_size = max(1, batch_size)
    processed = 0

    for start in range(0, total_lines, batch_size):
        batch_original = original_subs[start:start + batch_size]
        batch_translated = translated_subs[start:start + batch_size]
        batch_lines = []

        for i, (orig_line, trans_line) in enumerate(zip(batch_original, batch_translated), start=1):
            speaker = orig_line.name.strip() if orig_line.name else "Line"
            length_seconds = None
            if hasattr(orig_line, "start") and hasattr(orig_line, "end"):
                length_seconds = max(0.0, (float(orig_line.end) - float(orig_line.start)) / 1000.0)
            elif hasattr(orig_line, "length"):
                length_seconds = max(0.0, float(orig_line.length) / 1000.0)
            length_label = f"{length_seconds:.2f}s" if length_seconds is not None else "0.00s"
            batch_lines.append(
                f"{i}. {speaker} ({length_label}): {orig_line.text} => {trans_line.text}"
            )

        prompt = "\n".join(batch_lines)
        response = llm.infer(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature
        ).strip()

        reviewed_lines = [line for line in response.splitlines() if line.strip()]
        if len(reviewed_lines) != len(batch_lines):
            raise ValueError("Review output line count mismatch.")

        for reviewed, trans_line in zip(reviewed_lines, batch_translated):
            if ":" not in reviewed:
                raise ValueError("Missing ':' delimiter in review output.")
            _, reviewed_text = reviewed.split(":", 1)
            trans_line.text = reviewed_text.strip().replace("\\N", " ")
            processed += 1
            if progress_callback:
                progress_callback(processed, total_lines)

    return translated_subs

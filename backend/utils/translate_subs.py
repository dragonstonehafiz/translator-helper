from typing import Optional
from interface import LLMInterface
from utils.prompts import PromptGenerator
from utils.logger import setup_logger

translate_file_logger = setup_logger(name="translate-file")

def _is_rate_limit_error(error: Exception) -> bool:
    try:
        import openai
        return isinstance(error, openai.RateLimitError)
    except Exception:
        return False


def translate_sub(
    llm: LLMInterface,
    text: str,
    context: Optional[dict] = None,
    input_lang: str = "ja",
    target_lang: str = "en",
    temperature: float | None = None,
    max_tokens: int | None = None
):
    prompt_generator = PromptGenerator()
    system_prompt = prompt_generator.generate_translate_sub_prompt(
        context=context,
        input_lang=input_lang,
        target_lang=target_lang
    )
    return llm.infer(
        prompt=text.strip(),
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    ).strip()


def translate_sub_batch(
    llm: LLMInterface,
    lines: list[str],
    context: Optional[dict] = None,
    input_lang: str = "ja",
    target_lang: str = "en",
    temperature: float | None = None,
    max_tokens: int | None = None
):
    prompt_generator = PromptGenerator()
    system_prompt = prompt_generator.generate_translate_batch_prompt(
        context=context,
        input_lang=input_lang,
        target_lang=target_lang
    )
    batch_input = "\n".join(lines)
    response = llm.infer(
        prompt=f"{batch_input}",
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    ).strip()
    return [line for line in response.splitlines() if line.strip()]

def translate_subs(
    llm: LLMInterface,
    subs,
    context: dict,
    context_window: int = 3,
    input_lang: str = "ja",
    target_lang: str = "en",
    temperature: float | None = None,
    max_tokens: int | None = None,
    progress_callback=None
):
    total_lines = len(subs)
    batch_size = max(1, context_window)
    processed = 0

    for start in range(0, total_lines, batch_size):
        batch = subs[start:start + batch_size]
        context_dict = context.copy()
        batch_lines = []
        for i, line in enumerate(batch, start=1):
            speaker = line.name.strip() if line.name else "Line"
            batch_lines.append(f"{i}. {speaker}: {line.text}")

        for attempt in range(3):
            try:
                translated_lines = translate_sub_batch(
                    llm,
                    batch_lines,
                    context=context_dict,
                    input_lang=input_lang,
                    target_lang=target_lang,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if len(translated_lines) != len(batch_lines):
                    print("Batch input lines:")
                    for line in batch_lines:
                        print(line)
                    print("Batch translated lines:")
                    for line in translated_lines:
                        print(line)
                    raise ValueError("Batch translation output line count mismatch.")

                for idx, (line, translated) in enumerate(zip(batch, translated_lines), start=1):
                    if ":" not in translated:
                        raise ValueError("Missing ':' delimiter in batch translation output.")
                    _, translated_text = translated.split(":", 1)
                    original_line = f"{line.text}"
                    line.text = translated_text.replace("\\N", " ").strip()
                    translate_file_logger.info("Original: %s", original_line)
                    translate_file_logger.info("Translated: %s", line.text)
                    processed += 1
                    if progress_callback:
                        progress_callback(processed, total_lines)
                break
            except Exception as e:
                if _is_rate_limit_error(e):
                    import time
                    time.sleep(1.5)
                    continue
                raise

    return subs

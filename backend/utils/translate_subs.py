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
        prompt=f"<LINE>\n{text.strip()}\n</LINE>",
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    ).strip()

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
    for idx, line in enumerate(subs):
        if progress_callback:
            progress_callback(idx + 1, len(subs))

        prev_lines = subs[max(0, idx - context_window):idx]
        next_lines = subs[idx + 1:idx + context_window + 1]

        context_dict = context.copy()
        context_dict["Previous Lines"] = "\n".join([f"{l.name}: {l.text}" for l in prev_lines])
        context_dict["Next Lines"] = "\n".join([f"{l.name}: {l.text}" for l in next_lines])
        context_dict["Current Speaker"] = line.name

        try:
            length_seconds = None
            if hasattr(line, "start") and hasattr(line, "end"):
                length_seconds = max(0.0, (float(line.end) - float(line.start)) / 1000.0)
            elif hasattr(line, "length"):
                length_seconds = max(0.0, float(line.length) / 1000.0)

            if length_seconds is not None:
                context_dict["length_seconds"] = round(length_seconds, 2)
        except Exception:
            pass

        original_line = f"{line.text}"
        current_line = original_line
        for attempt in range(3):
            try:
                translation = translate_sub(
                    llm,
                    current_line,
                    context=context_dict,
                    input_lang=input_lang,
                    target_lang=target_lang,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                line.text = translation
                translate_file_logger.info("Original: %s", original_line)
                translate_file_logger.info("Translated: %s", translation)
                break
            except Exception as e:
                if _is_rate_limit_error(e):
                    import time
                    time.sleep(1.5)
                    continue
                break

    return subs

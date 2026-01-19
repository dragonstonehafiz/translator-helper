from typing import Optional


from interface.llm_interface import LLMInterface
from utils.prompts import PromptGenerator


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


def translate_subs(
    llm: LLMInterface,
    subs,
    context: dict,
    context_window: int = 3,
    input_lang: str = "ja",
    target_lang: str = "en",
    temperature: float | None = None,
    max_tokens: int | None = None
):
    for idx, line in enumerate(subs):
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

        current_line = f"{line.text}"
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
                break
            except Exception as e:
                if _is_rate_limit_error(e):
                    import time
                    time.sleep(1.5)
                    continue
                break

    return subs

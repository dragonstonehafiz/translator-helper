from typing import Optional
from interface import LLMInterface
from prompts.translate import generate_translate_sub_prompt
from prompts.translate_file import generate_translate_batch_prompt


def translate_sub(
    llm: LLMInterface,
    lines: list[str],
    context: Optional[dict] = None,
    input_lang: str = "ja",
    target_lang: str = "en",
    temperature: float | None = None,
    max_tokens: int | None = None
):
    system_prompt = generate_translate_batch_prompt(
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


def translate_single_line(
    llm: LLMInterface,
    line: str,
    context: Optional[dict] = None,
    input_lang: str = "ja",
    target_lang: str = "en",
    temperature: float | None = None,
    max_tokens: int | None = None
):
    system_prompt = generate_translate_sub_prompt(
        context=context,
        input_lang=input_lang,
        target_lang=target_lang
    )
    return llm.infer(
        prompt=line,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    ).strip()

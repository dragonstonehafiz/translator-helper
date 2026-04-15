def build_context_block(context: dict | None = None) -> str:
    context = context or {}
    context_lines = []
    for key, value in context.items():
        context_lines.append(f"- {key}: {value}")
    return "\n".join(context_lines) or "No additional context was provided."


def build_context_sections(context: dict | None = None) -> str:
    context = context or {}
    context_sections = []
    for key, value in context.items():
        if value:
            title = key.replace("_", " ").title()
            context_sections.append(f"### {title}\n\n{value}")
    return "\n\n".join(context_sections) if context_sections else "No additional context provided."

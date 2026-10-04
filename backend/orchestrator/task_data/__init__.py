"""
Typed data passed between tasks, split by workflow.

Every task declares one of these classes as its input and another as its output. Required fields have no
defaults, so a stage that forgets to supply one fails when the next object is built instead of several stages
later. A stage that adds required fields builds the next class with `extend()`; a stage that only changes
existing fields uses `dataclasses.replace()`.
"""

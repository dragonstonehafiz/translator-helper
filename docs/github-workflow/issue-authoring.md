# Issue Authoring

## Purpose

Procedure for turning a bug report, feature idea, or improvement request into a reviewable draft issue for this repository. This file owns the investigation, evidence-handling, scoping, and acceptance-criteria procedure. Field structure is defined in [Use the shared template](#use-the-shared-template); implementation detail lives in [`README.md`](../README.md)'s reference set.

This produces a **draft** for the user to review. It does not publish anything to GitHub.

Investigating and drafting is the default and requires no special authorization; publishing or modifying anything on GitHub is a separate, explicit action never implied by producing a draft — see [`repository-rules.md`](../repository-rules.md) for this repository's safety and permission boundaries.

## Authoritative inputs

- There is no issue template in this repository (no `.github/`); use the structure in this file.
- This repository's own documentation for the affected area — see [`README.md`](../README.md)'s ownership map.
- The current source code — authoritative over any documentation or prior issue when they disagree.

## Contents

- [When this applies](#when-this-applies)
- [Use the shared template](#use-the-shared-template)
- [Inspect current behavior](#inspect-current-behavior)
- [Track evidence and uncertainty](#track-evidence-and-uncertainty)
- [Define scope and outcomes](#define-scope-and-outcomes)
- [Write acceptance criteria](#write-acceptance-criteria)
- [Render the draft](#render-the-draft)
- [Review boundary](#review-boundary)
- [Final checklist](#final-checklist)

## When this applies

Use this procedure when asked to:

- draft a new issue;
- improve an existing issue draft;
- investigate whether some reported behavior warrants an issue;
- convert an informal request ("hey can we...", a chat message, a one-line complaint) into a reviewable repository issue.

Three distinct activities live under this umbrella — keep them distinct in what you say to the user:

- **Investigating and drafting** — reading code, forming a description, proposing acceptance criteria. This is the default and requires no special authorization.
- **Editing a local draft** — revising a draft already in progress based on feedback. Still just drafting.
- **Publishing or modifying a GitHub issue** — actually creating/editing a real issue via the GitHub CLI or the GitHub UI. This is a separate action (see [Review boundary](#review-boundary)) and is never implied by the act of drafting.

Related-issue or duplicate searching is not part of this procedure. Use context the user explicitly supplies (a linked issue, a pasted description) when relevant, but do not initiate a search as a drafting step.

## Use the shared template

Use one field set for every request — bugs, features, and enhancements alike: **Goals**, **Verified facts**, **Acceptance criteria**, and optional **AI context**, in that order. The repository has no GitHub issue form, so these fields are pasted into a plain issue body as `##` sections.

## Inspect current behavior

Never draft from documentation alone. Before writing:

1. Identify the affected application layer.
2. Load only the reference relevant to that layer from [`README.md`](../README.md)'s ownership map.
3. Inspect the actual current implementation directly (read the file, don't rely on a reference's paraphrase).
4. Trace enough data/control flow to verify the reported behavior actually happens the way it's claimed to — for a bug, this usually means finding the specific line(s) responsible; for a feature/enhancement, it means confirming the described gap actually exists.
5. Record concrete files and symbols (e.g. `path/to/file.py:183`) when they clarify the report.
6. If a reference and the source code disagree, trust the code, and say so in the draft rather than silently picking one.

## Track evidence and uncertainty

Every draft keeps facts, assumptions, and unresolved decisions distinct — don't let them blur together:

- **Verified facts** — confirmed by reading code, configuration, or an existing issue; or independently reproduced. If a reported behavior hasn't been verified yet, say so briefly rather than inventing evidence.
- **Assumptions** — reasonable, but not independently confirmed (e.g. "this likely affects a related case too, but that path wasn't traced").
- **Unresolved decisions** — choices that need maintainer or product direction, not something resolvable by reading more code (e.g. "should this be a hard error or a silent fallback?").

An unsupported assumption must never be presented as current behavior — phrase it as an assumption, explicitly. If an assumption would materially change scope or acceptance criteria depending on which way it resolves, promote it to an unresolved decision instead of leaving it buried as an assumption.

## Define scope and outcomes

- **Goals** — at most two short paragraphs explaining the proposed addition, change, or fix, and why it matters.
- **Verified facts** — succinct, relevant evidence from direct inspection: current behavior, affected users or workflows, relevant edge cases. Not an explanation of how the system works.
- Desired outcome is described as **observable behavior**, not a prescribed implementation.
- State explicit non-goals only when they materially bound scope; otherwise omit them rather than pad the draft.

Implementation detail may be included only when: it was confirmed by inspected code, it's required by a compatibility constraint worth flagging, or the user explicitly asked for a specific implementation — put it in AI context, not Goals.

## Write acceptance criteria

Each criterion:

- is a Markdown checkbox carrying a sequential identifier — `- [ ] **AC-1:** ...`, `- [ ] **AC-2:** ...`, and so on, numbered without gaps;
- describes exactly one observable result;
- covers an outcome that is essential to considering the issue done;
- does not duplicate or substantially overlap another criterion;
- is independently verifiable (someone else could check it without asking the author what they meant);
- avoids vague wording like "works correctly" or "handles edge cases properly" — name the actual edge case;
- includes compatibility/non-regression expectations where relevant.

Consolidate criteria that describe the same observable result. Two checkboxes that a reviewer would verify with the same check are one criterion, not two — merge them and keep the wording that names the outcome most concretely.

Five criteria is the default maximum. Exceeding it is allowed only when the additional criteria are independently essential, describe distinct outcomes, and cannot reasonably be consolidated — never as a way to enumerate implementation steps or restate the same result in different words.

For documentation-only work, criteria should name the expected files, which document canonically owns the content, what validation was run, and confirm no runtime/application files changed.

Do not turn a speculative implementation step ("refactor X to use Y") into an acceptance criterion — acceptance criteria describe outcomes, not a plan.

## Render the draft

Render the issue title and every field as separate user-facing items:

- Present the proposed title as ordinary text outside a code fence, immediately followed by its own fenced `markdown` block containing only the title text.
- Present each field label as ordinary text outside a code fence.
- Immediately follow each label with its own fenced `markdown` block containing only the value to paste into that field.
- Never wrap the entire issue in one large code fence.
- Never put field labels such as `## Goals` or explanatory text such as "copy this" inside a field's code block.
- Keep assumptions/unresolved-decision summaries and other handoff commentary as ordinary text outside all copyable blocks.
- Preserve the template's field order: Goals, Verified facts, Acceptance criteria, AI context. AI context still gets its own block when it has content; omit it entirely when it has no content.

Use this output shape:

````text
Title

```markdown
Proposed issue title
```

Goals

```markdown
...
```

Verified facts

```markdown
...
```

Acceptance criteria

```markdown
- [ ] **AC-1:** First verifiable outcome describing the completed behavior
- [ ] **AC-2:** Second verifiable outcome covering compatibility or a named edge case
```

AI context

```markdown
...
```
````

`AI context` is optional and should be omitted when it has no content.

Do not add empty subheadings just to look complete. Omit a subsection that has nothing in it, or write "None identified" only where that absence is itself meaningful information.

## Review boundary

This procedure ends at a reviewable draft, not a published issue. Before considering the draft done:

1. Present the complete draft to the user.
2. Summarize the assumptions and unresolved decisions in a short list — don't make the user re-read the whole draft to find them.
3. If unresolved decisions remain, ask the user for direction on those specifically rather than guessing.

Creating or editing an actual GitHub issue is a separate, explicit action outside this procedure's scope — never assumed just because a draft was produced.

## Final checklist

- [ ] Current behavior confirmed by inspecting actual code, not asserted from documentation alone
- [ ] Relevant local documentation consulted (only what's relevant to the affected layer)
- [ ] No related-work/duplicate search initiated or implied
- [ ] Verified facts, assumptions, and unresolved decisions kept distinct
- [ ] Desired outcome stated as observable behavior, not an unverified implementation
- [ ] Acceptance criteria are observable, verifiable, and free of vague wording
- [ ] Every criterion is essential; overlapping or duplicate criteria consolidated into one
- [ ] Criteria carry sequential `AC-1`, `AC-2`, ... identifiers with no gaps
- [ ] No more than five criteria, unless the extras are distinct essential outcomes that cannot reasonably be consolidated
- [ ] Title and field labels rendered as ordinary text; each populated field (including title) has its own `markdown` code block containing only pasteable content
- [ ] No single code block wraps multiple issue-form fields or handoff commentary
- [ ] Draft presented for review, with assumptions/unresolved decisions summarized

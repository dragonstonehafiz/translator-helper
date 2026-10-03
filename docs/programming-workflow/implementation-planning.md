# Implementation Planning

## Purpose

Procedure for turning an approved issue, local issue file, or scoped request into an evidence-backed, dependency-ordered implementation plan. This produces a **plan**, not a change — it never implements, commits, or pushes anything.

Use this procedure when asked to plan an implementation, break a request into dependency-ordered steps, assess compatibility or existing-data impact, or revise an existing plan after requirements change. Read this file in full before planning.

Never create commits, run `git push`, or publish anything remotely — see [`repository-rules.md`](../repository-rules.md) for this repository's full safety and permission boundaries. Producing a plan never authorizes implementing it.

## Authoritative inputs

- The approved issue, local issue file, or current scoped request, and its acceptance criteria.
- Related issues, PRs, or dependencies already identified.
- A supplied plan file to revise, when the user hands one off.
- This repository's own documentation — start from [`README.md`](../README.md)'s ownership map to find the reference for the affected area — and [`repository-rules.md`](../repository-rules.md) for coding rules, verification commands, and safety boundaries.
- The current source code and current working-tree state — both take priority over documentation and any prior plan when they disagree.

## Contents

- [When this applies](#when-this-applies)
- [Establish scope](#establish-scope)
- [Select references by affected area](#select-references-by-affected-area)
- [Inspect the implementation](#inspect-the-implementation)
- [Track evidence and uncertainty](#track-evidence-and-uncertainty)
- [Control scope](#control-scope)
- [Order implementation steps](#order-implementation-steps)
- [Plan existing-data handling](#plan-existing-data-handling)
- [Define focused verification](#define-focused-verification)
- [Write the plan file](#write-the-plan-file)
- [Review boundary](#review-boundary)
- [Final checklist](#final-checklist)

## When this applies

Use this procedure when asked to:

- create an implementation plan;
- break an issue or request into implementation steps;
- identify affected files and confirmed dependencies;
- assess compatibility or existing-data impact;
- revise an existing plan after requirements change.

Three distinct activities live under this umbrella:

- **Investigating the implementation** — reading code, tracing flow, forming the plan. The default; needs no special authorization.
- **Producing or revising a plan** — still just planning, even across multiple rounds of feedback.
- **Implementing the plan** — writing actual code changes. A separate action, never implied by having a plan (see [Review boundary](#review-boundary)).

## Establish scope

Start from:

- the approved issue, local issue file, or current request;
- its acceptance criteria;
- related issues/dependencies already identified;
- applicable local documentation;
- current source code;
- current working-tree state, when local uncommitted changes could affect the plan (check `git status` before assuming a clean baseline).

If the request and the issue or file it references disagree, record the conflict explicitly rather than silently picking one interpretation.

When the user supplies a plan file to revise, treat it as the current authoritative draft rather than starting over: reconcile it against the current request, current source, and current working tree — which still take priority over prior plan text and documentation when they disagree — preserve still-valid evidence and decisions, replace stale content, update its status, and write the result back to that same file in place.

When no destination is supplied, save a new plan as a local Markdown file under `<repository-root>/.plans/`, using a simple descriptive filename (for example, derived from an issue number or a short slug of the request). Locate the repository root using the destination repository's own workspace conventions rather than assuming a path from another project.

## Select references by affected area

Load only what's relevant to the areas the change touches — expand as tracing reveals a dependency, don't load everything up front. [`README.md`](../README.md) is this repository's ownership map from task area to canonical reference (`architecture.md`, `tasks.md`, `api.md`, `frontend.md`, `verification.md`, under `docs/references/`).

## Inspect the implementation

Before proposing steps:

1. Identify the user-visible or system-level entrypoint.
2. Locate the relevant files and symbols.
3. Read their current implementation.
4. Trace callers and downstream consumers.
5. Inspect related types, interfaces, queries, and styles.
6. Check what pattern the codebase already uses for similar behavior.
7. Check whether related local changes already exist in the working tree.

A plan must not name a file or symbol as fact unless it was actually verified this way. When an exact location can't be confirmed, mark it as an assumption rather than inventing a plausible-looking path.

Where the work crosses layer boundaries (for example: external source, ingestion/business logic, persistence, a query/read layer, an API contract, a client integration, shared types, a user-facing surface), describe the affected flow only to the extent needed to justify step order and dependencies below — a full flow diagram or an exhaustive layer-by-layer report isn't required for simple, single-layer work.

## Track evidence and uncertainty

Maintain four distinct categories, recorded in the relevant step's context rather than as standalone plan sections:

- **Confirmed details** — verified from current code or configuration.
- **Assumptions** — plausible, not yet verified; pair each with a verification step that would catch it being wrong.
- **Unresolved decisions** — choices requiring user or maintainer direction.
- **Risks and compatibility concerns** — ways the implementation could regress existing behavior.

If an unresolved decision would substantially change the implementation, stop and ask before presenting one approach as final — present the decision and the affected alternatives instead of picking one silently. Resolve routine implementation details autonomously. Never present an unresolved consequential choice as an implementation-ready instruction.

## Control scope

Restate: desired outcome, in-scope behavior, explicit non-goals, affected users/workflows, compatibility expectations.

When the issue or request already supplies acceptance criteria, reuse their wording and identifiers rather than silently rewriting or reducing them. If later instructions conflict with them, explain the conflict and apply the explicit correction; ask when its implications remain unclear.

When criteria are absent, author them following the same standards as issue drafting:

- sequential `- [ ] **AC-1:** ...`, `- [ ] **AC-2:** ...` checkboxes, numbered without gaps;
- each describes exactly one observable, independently verifiable result essential to considering the work done;
- consolidate criteria that a reviewer would check with the same test rather than listing near-duplicates;
- include relevant compatibility/non-regression expectations, and documentation-only verification requirements for documentation-only work;
- five criteria is the default maximum — exceed it only when additional criteria are independently essential, describe distinct outcomes, and cannot reasonably be consolidated.

Every implementation step must map to one of: an acceptance criterion, a confirmed dependency, required verification, or required documentation maintenance. Required documentation maintenance means each reference whose content the change alters — see [`documentation-maintenance.md`](../documentation-workflow/documentation-maintenance.md). Unrelated cleanup, refactoring, dependency upgrades, and style changes are excluded unless explicitly approved — when useful cleanup is spotted along the way, list it as follow-up work rather than folding it into the plan.

## Order implementation steps

Order steps by actual dependencies in this change, not by a fixed application-wide layer sequence and not by UI order. Skip unaffected areas rather than listing a step with nothing to do. Avoid code-level pseudocode or line-by-line edits unless a fragile algorithm genuinely requires it — clear prose is enough when it leaves no material choice unresolved.

## Plan existing-data handling

There is no database; persistent state is JSON on disk — series library files under `backend/files/library/<series_id>/` and per-provider settings in `backend/files/config/*.json` (see [`architecture.md`](../references/architecture.md#storage)). When a change alters the shape of either, determine how existing files reach the required state: tolerant reads with defaults (as `load_series` does for missing `characters.json`/`glossary.json`), a one-off conversion, or an explicitly approved reset. Backward compatibility between application versions and rollback support are not required unless the request asks for them.

In-memory task state (results, progress) is rebuilt on every restart and needs no migration. Any deletion of library, settings, or output files requires explicit approval.

Omit this concern entirely from steps where it doesn't apply — don't invent version-compatibility requirements the request never asked for.

## Define focused verification

Select checks proportional to what actually changed, using [`verification.md`](../references/verification.md)'s commands (`py_compile`, `tsc`, plus the manual browser checks the user will run) scoped to the changed files or layer rather than a full project-wide build by default. Typical proportionate selection:

- a changed backend file: `py_compile` that file;
- a changed frontend file: `tsc` type check, plus a template check when templates change;
- an API change: exercise success, validation, error, and compatibility cases;
- a library-storage change: verify existing series still load, missing files/fields fall back to defaults, and saves round-trip;
- a task or chain change: verify pass-through of upstream data, progress reporting, the final task's result, run-log output, and failure handling (error surfaces in the poll response);
- a UI change: verify loading, empty, error, and in-progress (progress overlay) states;
- a documentation-only change: documentation checks plus confirmation that no application files changed.

A full build is never the default verification step — it still requires explicit approval per the destination repository's own policy. Verification should prove the acceptance criteria are met, not merely that files compile. Every acceptance criterion must be covered by at least one step's changes or verification.

## Write the plan file

Create the plan file at the destination established in [Establish scope](#establish-scope), or open the supplied file and revise it in place. The file is the plan; nothing about the required content changes when it is a revision rather than a first draft.

```markdown
# Implementation Plan: <short descriptive title>

## Plan identity

- **Objective:** <one-line statement of what this plan achieves>
- **Status:** <Draft / Ready for review / Revised — brief reason>

## Objective

<Up to two short paragraphs: what this plan achieves and why.>

## Files touched

- `<path>`: <brief purpose>

## Confirmed current behaviour

<Concise, plain-language description of what the code currently does, verified against source.>

## Scope

### In scope

<Concise, plain-language list of in-scope behavior.>

### Acceptance criteria

- [ ] **AC-1:** ...

## Non-goals

- <explicit exclusion>

## Implementation

### 1. Step title

**Objective:** <what this step achieves, briefly>

**Files updated:** <paths>

**Necessary context:** <what's already true, confirmed dependencies, relevant assumptions>

**Changes to make:** <concrete edits and required behavior, without leaving material choices unresolved>

**Verification:** <focused check(s) for this step>

### 2. ...
```

Files touched lists the expected files with brief purposes — it is advisory, not exclusive; a verified dependency may justify touching another file within the task's scope. Non-goals stays a separate section, listing explicit exclusions. Omit a plan-level section only when it would be empty for genuinely trivial work; do not omit Acceptance criteria or Non-goals.

Save the file before responding. The response that follows is a pointer to it plus a concise summary, not a duplicate of its content (see [Review boundary](#review-boundary)).

## Review boundary

Before declaring the plan ready:

1. Confirm the plan file was created, or the supplied plan was revised in place, at the intended path.
2. In the response, give the path (as a clickable link where the surface supports it) plus a concise status summary: readiness/status, major scope, assumptions or unresolved decisions worth flagging, and any destructive or compatibility-sensitive steps. Do not reproduce the complete plan in the response — the file is authoritative.
3. Confirm every acceptance criterion is covered by at least one step or verification item.
4. Ask for direction on any material unresolved decision.
5. Wait for explicit authorization before implementing anything.

When handing the plan to another agent or a later session, communicate its file path so it can be reopened and revised there instead of recreated.

Producing or revising a plan file is never itself authorization to implement it, and the destination repository's own git and safety restrictions apply throughout — no commits, no pushes, no remote publication, regardless of how much of the plan has been reviewed.

## Final checklist

- [ ] Scope established from the approved issue/request, with any conflict against it recorded
- [ ] Only relevant local documentation loaded, expanded as needed
- [ ] Relevant files and symbols actually inspected, not assumed
- [ ] Confirmed details, assumptions, unresolved decisions, and risks kept distinct and placed in the relevant step
- [ ] Supplied acceptance criteria preserved verbatim; newly authored criteria follow the compact AC rules above (sequential, verifiable, consolidated, five-max by default)
- [ ] Non-goals stated; unrelated work excluded or listed as follow-up
- [ ] Steps ordered by actual dependency, each with Objective, Files updated, Necessary context, Changes to make, and Verification
- [ ] Existing-data handling addressed explicitly wherever library or settings file shapes change, and omitted where it doesn't apply
- [ ] Verification is focused per step, not a default full build
- [ ] Every acceptance criterion maps to a step or verification item
- [ ] Plan file saved at its path; response gives that path plus a concise summary, not the full plan; implementation requires explicit authorization, while commits, pushes, and remote publication remain prohibited

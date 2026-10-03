# Commit Message Authoring

## Purpose

Procedure for drafting a commit message from the actual state of the changes being committed. This produces a **draft** for the user to commit with themselves. It never stages files or creates a commit.

This is a drafting step only — see [`repository-rules.md`](../repository-rules.md) for this repository's safety and permission boundaries.

## Authoritative inputs

- Recent history (`git log --format=%s -20`) — this repository has no commit hook or `CONTRIBUTING.md`; history mixes Conventional Commits subjects (`feat: ...`, `fix: ...`) with plain lowercase ones. Use the Conventional Commits format below unless the user asks otherwise.
- The current `git status` and diff, staged and unstaged, of the changes being committed.

## Contents

- [When this applies](#when-this-applies)
- [Format](#format)
- [Write the subject](#write-the-subject)
- [Write the bullets](#write-the-bullets)
- [Render and hand off](#render-and-hand-off)
- [Example](#example)

## When this applies

Use this procedure when asked to write or suggest a commit message. Producing a draft never authorizes staging or committing.

## Format

```
<type>(<optional-scope>): <description>

- <main change>
- <main change>
```

One subject line, a blank line, then a bullet list.

## Write the subject

- Use one of these types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`, `build`, or `ci`. Pick it from what the diff does as a whole.
- Add `!` before the colon only for a breaking change the user or the diff confirms.
- Write the description in lowercase, in the imperative, with no trailing period. Keep it to one short line naming the change, not a list of what it touched.

## Write the bullets

- List only the main changes: what a reader of the history needs to know. Leave out small follow-ups, file-by-file detail, test counts, and verification results.
- One change per bullet, as a short imperative phrase starting with a capital letter, with no trailing period.
- Name shared code by the names a reader will search for (components, hooks, files). Group related changes into one bullet rather than one per file.
- Cover documentation in one bullet when the commit updates docs.
- Describe only what the diff contains, including changes the user made or staged earlier that are part of the same commit.

## Render and hand off

Present the whole message as a single fenced block, exactly as it should be committed. Afterwards, point out as ordinary text anything the user should check, such as changes in the working tree that are not part of the commit. Do not stage or commit.

## Example

```
feat: add library context selection to translation chains

- Add TaskSelectLibraryContext and TaskSelectLibraryContextForReview to the translate and review chains
- Pass series_id from the Translate page so file translation and review can use the series library
- Fix pass-through in chain tasks that dropped upstream data
- Update reference docs
```

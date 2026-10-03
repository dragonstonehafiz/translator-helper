# Pull Request Authoring

## Purpose

Procedure for drafting a PR title and a template-compatible PR body from the actual state of a branch's changes, using this repository's own conventions. This produces a **draft** for the user to copy into `gh pr create` or the GitHub UI themselves. It never creates a commit, stages files, pushes a branch, or opens/publishes a pull request.

"PR message" means both the title and the body together.

This is a drafting step only — see [`repository-rules.md`](../repository-rules.md) for this repository's safety and permission boundaries around publishing.

## Authoritative inputs

- This repository has no PR template, `CONTRIBUTING.md`, or CI. Use the default sections in [Fill the template](#fill-the-template), and the title format from [`commit-message-authoring.md`](commit-message-authoring.md#write-the-subject). Branches follow `feat/<name>` and `release/<version>`; PRs target `main`.
- [`verification.md`](../references/verification.md) — what a completed check for a given layer looks like.
- The current `git status` and diff for the branch being described.
- Verification results actually run and reported earlier in the conversation, or told directly to the agent by the user.

## Contents

- [When this applies](#when-this-applies)
- [Gather evidence](#gather-evidence)
- [Select the title](#select-the-title)
- [Fill the template](#fill-the-template)
- [Avoid fabrication](#avoid-fabrication)
- [Render and hand off](#render-and-hand-off)
- [Final checklist](#final-checklist)

## When this applies

Use this procedure when asked to write, draft, or revise a PR title, PR description, PR body, or PR summary for the current branch's changes.

This is a drafting step only. Producing a draft never authorizes staging, committing, pushing, or creating/publishing an actual pull request — those remain separate, explicit actions the user takes themselves.

## Gather evidence

Before drafting anything:

1. Inspect the full set of changes the PR would contain: the diff of the branch against its base, plus any staged or unstaged working-tree changes on top of it. A clean working tree does not mean there's nothing to describe — most of a real PR's content is already committed on the branch. The draft describes what actually changed across all of that, not what the request implies changed.
2. If an issue was supplied or referenced earlier in the conversation, read it for the relationship it actually establishes (fixes it, is merely related to it, etc.) — don't assume closure just because one was mentioned.
3. Collect verification evidence **only from what has already been run and reported** — earlier in this conversation, or directly stated by the user. Do not run any verification commands as part of drafting; this procedure reports on evidence that already exists, it doesn't generate it.
4. If the diff spans changes that don't obviously belong together (e.g. an unrelated refactor mixed into a bug fix), say so rather than presenting it as one clean, coherent PR.
5. If the branch matches its base and the working tree is clean — nothing to describe — say that plainly and ask for the missing evidence rather than inventing a summary.

## Select the title

- Use the Conventional Commits subject format from [`commit-message-authoring.md`](commit-message-authoring.md#write-the-subject).
- Pick the type or category from what the diff actually does — new capability, correction, or maintenance/tooling, mapped to whatever categories the destination repository actually uses.
- Mark a breaking change only when explicitly confirmed (by the user or unambiguously by the diff itself) — never speculate about breaking-ness to decide this.
- If the repository's convention makes the PR title the squash commit message, keep it a single accurate line, not a summary of every file touched.

## Fill the template

With no repository template, use exactly these four sections, in this order:

- **Summary** — describe the behavior change and why, in prose. Not a file-by-file list; that's what the diff itself already shows.
- **Related issue** — use a closing keyword only when the request or issue explicitly establishes that this PR resolves it; use a looser relation phrase when the connection is looser. Keep the section heading even when no issue was supplied — state that explicitly rather than dropping the section; never invent a number.
- **Testing** — list only the verification commands actually run and reported, with their actual results. State plainly which applicable checks were not run rather than omitting them silently.
- **Checklist** — check a box only when the gathered evidence actually supports it. Leave a box unchecked when the evidence doesn't cover it, rather than checking it optimistically.

## Avoid fabrication

Never invent: an issue number, a test result, a screenshot, a "no breaking changes" claim, or a checklist state not backed by evidence gathered above. Where evidence is missing, the draft says so explicitly instead of presenting an optimistic guess as fact.

## Render and hand off

GitHub's PR creation page has one title field and a single Markdown textarea for the whole body — unlike issue forms (which have separate structured fields per label, see `issue-authoring.md`), there's nothing to split the body into. Render accordingly:

- Present the proposed title as ordinary text outside a code fence: `Title: <proposed title>`.
- Present the entire body — every template section, in template order — as a single fenced `markdown` block, exactly as it should be pasted into that one textarea.
- Never put the title inside the body's code block, and never split the body across multiple blocks.

After the rendered draft, point out as ordinary text anything the user should double-check (an assumed issue relationship, a checklist item left unchecked for lack of evidence, a diff that looked mixed-scope). Do not stage, commit, push, or create/publish the PR — that is the user's action to take with the draft.

## Final checklist

- [ ] Evidence gathered from the actual branch-vs-base diff and working-tree state, not assumed from the request
- [ ] Verification evidence used only from what was already run/reported — no checks run proactively by this procedure
- [ ] Title matches the destination repository's enforced format, with breaking-change marking only for confirmed breaking changes
- [ ] Body matches the current PR template's sections exactly, nothing added or removed
- [ ] Related-issue wording matches the actual, stated relationship
- [ ] Testing section lists only real commands and real results; unrun checks stated plainly
- [ ] Checklist boxes reflect only what the evidence supports
- [ ] Draft handed off for the user to publish themselves — no git or GitHub action taken

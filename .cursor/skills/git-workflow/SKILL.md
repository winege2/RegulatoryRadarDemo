---
name: git-workflow
description: >-
  Enforces this repository's Git workflow whenever the agent edits, adds, or
  deletes project files. Use on every coding task—features, bugfixes, docs,
  refactors, config, or tests—even if the user only says "fix this" or "add
  X". Requires working off main only via feature branches (feat/, fix/, docs/),
  never committing secrets, and finishing with push + pull request (never merge).
  Also use when the user mentions branches, commits, push, PR, merge request, or
  "wrap up" work.
---

# Git workflow (Regulatory Radar)

Follow this workflow **before the first file edit** and through **task completion**. It applies to all code and doc changes in this repo unless the user explicitly opts out of Git steps for a specific request.

## Non-negotiable rules

Use these rules verbatim; do not weaken or skip them:

1. **Never work on `main`.** Do not commit directly to `main`. If you are on `main`, stop and create a branch before changing files.
2. **Before changing code:** update `main`, then create a branch:
   - `feat/...` — new behavior or enhancements
   - `fix/...` — bug fixes
   - `docs/...` — documentation-only changes
   Use short, kebab-case suffixes (e.g. `feat/version-endpoint`, `fix/openfda-timeout`).
3. **Never commit secrets.** Do not stage or commit `.env`, credentials, private keys, tokens, or similar. If unsure, check `git status` and `git diff` before every commit. `.env.example` and other intentional samples are fine when they contain no real secrets.
4. **When the work is done:** push the branch and open a **pull request to `main`** with a short description covering:
   - **What changed**
   - **Why**
   - **How it was tested**
5. **Never merge the PR.** A person merges after review and green CI. Do not run merge commands or approve/merge via `gh`.

## Before you edit any file

1. Confirm the default branch is `main` (`git symbolic-ref refs/remotes/origin/HEAD` or `git branch -r`).
2. Fetch and update local `main` (PowerShell-friendly):

   ```powershell
   git fetch origin
   git checkout main
   git pull origin main
   ```

3. Create and switch to the branch:

   ```powershell
   git checkout -b feat/short-description
   ```

   Pick `feat/`, `fix/`, or `docs/` from the change type. If the user already created a suitably named branch for this task, stay on it after ensuring `main` was pulled (rebase or merge from `main` only when needed to avoid conflicts).

## While working

- Keep changes scoped to the task.
- Prefer [conventional commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`) with a clear subject. Commit on the feature branch when the user asks for a commit or when you are finishing the requested work—not drive-by commits on unrelated files.
- Never use destructive Git commands (`push --force` to `main`, `reset --hard`, etc.) unless the user explicitly requests them.
- Never change `git config`. Never skip hooks (`--no-verify`) unless the user explicitly requests it.

## Finishing: push and open a PR

1. Ensure the working tree reflects what should be reviewed (committed unless the user asked for a draft PR without commits—rare).
2. Push the branch:

   ```powershell
   git push -u origin HEAD
   ```

3. Open a PR to `main` with `gh` (this repo uses GitHub):

   ```powershell
   gh pr create --base main --title "feat: short title" --body "$( @'
   ## Summary
   - What changed (bullets)

   ## Why
   One or two sentences.

   ## Test plan
   - [ ] How you verified (commands run, manual checks)

   '@ )"
   ```

   Adjust the title prefix to match the branch type. Return the PR URL to the user.

4. Remind the user that **they** merge after review and CI passes.

## If the user only wanted a quick local edit

Still **branch before editing**. If they say not to push or open a PR, honor that—but do not commit on `main` or commit secrets.

## Quick checklist

| Step | Done? |
|------|--------|
| On a `feat/`, `fix/`, or `docs/` branch (not `main`) | |
| `main` was pulled before branching | |
| No `.env` or secrets in the commit | |
| Branch pushed | |
| PR opened to `main` with what / why / tested | |
| PR left open for human merge | |

---
name: wrap-up
description: Post-implementation checklist. Walks through verify → update docs → code-review → generate report → rename session → commit (PR optional) → deploy. Use when the user says "wrap up", "finalize feature", "ready to ship", "done with this feature", or invokes /wrap-up.
---

# wrap-up — post-implementation checklist

Run these steps in order. Stop and surface failures rather than pushing through.

## 1. Verify correctness

- Invoke `/verify` (the `verify` skill) to execute the implementation plan's Test plan section. It handles plan lookup, skip-if-already-run, command resolution, and per-item pass/fail reporting.
- Wait for `/verify` to finish. If any check fails, **stop here** — do not continue to later steps until the user resolves it.

## 2. Update docs

- Invoke `/update-docs` (the `update-docs` skill) scoped to the current diff. That skill detects the project's doc layout, proposes a per-file update plan, and waits for confirmation before editing.
- Wait for `/update-docs` to finish before continuing.

## 3. Code review

- Invoke `/code-review` (the `code-review` skill) to run a multi-agent review of the diff (including the doc updates from step 2). It writes findings to `REVIEW.md` filtered through a confidence threshold.
- Read `REVIEW.md`. If it has `status: issues_found`, surface the findings to the user and pause for them to decide which to fix.
- Items the user fixes: fix them, then re-run `/code-review` to confirm. Items the user defers: note them so step 4 (report) carries them into the report's `# Unsolved Issues` section. Items the user fixed during this step go into the report's `# Updates` section.
- Wait for `/code-review` and any user fixes to finish before continuing.

## 4. Generate report

- Invoke `/report` (the `report` skill) to capture what was done — conversation, file changes, actions — into `docs/reports/YYYY-MM-DD-[title].md`.
- Skip if the change is trivial (typo, single-line fix) or the user opts out.

## 5. Session hygiene

- After saving the report (and any plan integration), invoke the `rename-session` skill with the report's `YYYY-MM-DD-[title]` as the argument so the session name matches the report. For multiple reports, use the first report's title.

## 6. Commit (PR optional)

- Stage specific files (avoid `git add -A`, which can grab secrets or unrelated junk).
- Write the commit message focused on **why**, not what. Follow the repo's existing commit style (check `git log` for tone).
- Commit.
- **Do not open a PR by default.** After the commit, ask the user: _"Open a PR?"_
  - If yes: confirm before pushing, then push and run `gh pr create` with a summary + test plan.
  - If no: stop here.
- ASK FIRST before any push, force-push, or destructive git operation.

## 7. Deploy

Three branches, evaluated in order. The first match wins; each branch ends the step.

Remember:

- Never run a deploy command without explicit user confirmation in the same turn.
- Never re-deploy if Branch B detected an earlier deploy in this session — confirm only.
- Skip cleanly when CI/CD is detected — don't manufacture a manual deploy.

### Branch A — CI/CD handles deploy → skip

If any of these signals are present, print `CI/CD handles deploy on merge — skipping.` and end:

- `.github/workflows/*.yml` contains a deploy job (uses `vercel-action`, `superfly/flyctl-actions`, `cloudflare/wrangler-action`, `aws-actions/*`, `JamesIves/github-pages-deploy-action`, etc., or a job named `deploy` / `release` / `publish` triggered on push to main).
- `vercel.json` or `.vercel/` exists (assume Vercel Git integration unless docs say otherwise).
- `fly.toml` plus a `.github/workflows/fly*.yml`.
- `netlify.toml` (Netlify Git integration).
- `AGENTS.md` / `CLAUDE.md` / `README.md` says "deploys automatically on merge", "CI deploys", "auto-deploy".

### Branch B — Already deployed in this conversation → confirm

If Branch A didn't match, scan this session's transcript for prior deploy signals:

- Bash commands like `vercel`, `vercel deploy`, `fly deploy`, `flyctl deploy`, `wrangler deploy`, `wrangler publish`, `gh workflow run`, `git push heroku`, `git push dokku`, `firebase deploy`, `netlify deploy`, `eb deploy`, `kubectl apply`, `helm upgrade`, `terraform apply`.
- Tool outputs containing deploy URLs (`*.vercel.app`, `*.fly.dev`, `*.workers.dev`, `*.netlify.app`, `*.web.app`, custom domains from docs).
- User messages saying "I deployed", "deployed to <url>", "shipped it".

If found, print `Looks like deploy already happened in this session: <evidence>. Done.` and end. Do not re-deploy.

### Branch C — Ask the user, then offer to deploy

Ask the user: _"Have you deployed this change manually (outside this session)?"_

- **Yes** → end.
- **No** → run deploy-docs detection and offer to deploy:

  1. Look for deploy instructions in `AGENTS.md` / `CLAUDE.md` / `README.md` (sections titled "Deployment", "Deploy", "Release", "Shipping"), `docs/deploy*`, `docs/deployment*`, `docs/release*`, `docs/runbook*`. Also note provider configs: `Dockerfile`, `Procfile`, `fly.toml`, `vercel.json`, `wrangler.toml`, `netlify.toml`, `app.yaml`, `serverless.yml`, `package.json`.
  2. Show the user the doc excerpt, the exact command(s) to run, and any preconditions the docs mention (env vars, login state, branch).
  3. **Wait for explicit user confirmation before executing.** Never run a deploy command without the user saying go in the same turn.
  4. On confirm, execute. On failure, surface output and stop — do not retry or fall back to a different command.
  5. After successful deploy, if a URL was emitted or detected from docs, print `Reminder: verify deploy at <url>`.

- If no deploy docs are found in the "no" branch: tell the user `No deploy docs found. Add deploy instructions to AGENTS.md or docs/deploy.md and re-run wrap-up.` and end.
- Never invent deploy commands. If docs are silent, stop and tell the user — don't guess `yarn deploy`, `npm run deploy`, `make deploy`, etc.

## Guardrails

- Match the global "executing actions with care" rules.
- If `/verify` reports any failure, stop the wrap-up flow.
- Never push or open a PR without explicit user confirmation.

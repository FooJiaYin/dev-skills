---
name: wrap-up
description: Post-implementation checklist with two modes. Full mode walks verify → update docs → code-review → report → rename session → cleanup → commit → deploy → improve (for the primary developer). Quick mode skips quality/deploy gates and ships report + commit + push only (for a time-constrained / non-git-literate collaborator, or when auto-invoked from /sync). Use when the user says "wrap up", "finalize feature", "ready to ship", "done with this feature", or invokes /wrap-up.
---

# wrap-up — post-implementation checklist

Two modes:

- **Full** — comprehensive flow for the primary developer. Interactive popups at every decision. See `./full.md`.
- **Quick** — minimal flow for git-illiterate collaborator or `/sync` auto-invoke. Zero-noise, smart staging, only critical popups. See `./quick.md`.

## Mode selection

- If invocation context says "from /sync — go straight to Quick mode" → run Quick (read `./quick.md`), no popup.
- If no mode mention, AskUserQuestion popup (header: "Wrap-up mode") — Quick (default) vs Full. Then read and execute the matching file.

## Common guardrails

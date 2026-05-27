# setup-notion — dangling-symlink guard + parent-folder import

**Date:** 2026-05-27
**Skill:** `setup-notion`
**Trigger:** Friction in iBadminton session where `setup-notion` overwrote an untracked-but-loadbearing `AGENTS.md` because its `Read` returned "doesn't exist" (the file was the target of a tracked `CLAUDE.md` symlink, but never committed itself).

## What changed

`skills/setup-notion/SKILL.md`:

1. **Step 4 (Write to disk) — added a dangling-symlink branch.**
   Before treating `AGENTS.md` as missing, the skill now checks whether `CLAUDE.md` is a tracked symlink pointing at it (`git ls-files -s` → mode `120000`, or `readlink`). If so, STOP and prompt the user — never overwrite blindly.

2. **Step 3 (Prompt only for missing fields) — added parent-folder import.**
   If `../AGENTS.md` contains a `## Notion` section, offer `Import from ../AGENTS.md` as the first option of the first prompt, with a URL preview. Accept → copy the section verbatim, skip per-field prompts. The option is omitted entirely when no parent match exists, keeping the prompt clean for fresh repos.

## Why

- The dangling-symlink bug clobbered real user data in iBadminton. The fix is defensive: the skill must treat a tracked-symlink-with-missing-target as "ask first" rather than "create fresh."
- The parent-folder import generalizes a manual workflow the user already had (passing `from sibling folder` as a skill arg) so future repos inherit org-shared Notion config in one click.

## Companion edit (out of this repo)

Added a broader `## Symlinks and dangling targets` section to `~/.claude/CLAUDE.md` so the dangling-symlink guard applies to any Write across all projects, not just `setup-notion`.

## Open questions

- Should parent-folder import walk further than immediate parent? Decided no — kept scoped to `../AGENTS.md` per user direction. If repos commonly nest deeper, can extend later.
- Should the import option auto-skip the import prompt entirely when CWD's `AGENTS.md` is missing? Currently still shows as one option among the prompt's choices. Left for usage to inform.

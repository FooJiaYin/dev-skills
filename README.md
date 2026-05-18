# dev-skills

A collection of reusable Agent Skills for software development workflows. Built for Claude Code as a plugin; the individual `SKILL.md` files are also usable by any agent that reads the Agent Skills format.

## Skills

Grouped by workflow:

- **[Spec authoring](#spec-authoring)** — turn requirements into a structured spec before coding.
- **[Dev flow](#dev-flow)** — discuss → implement → wrap up a feature.
- **[Notion integration](#notion-integration)** — bridge between local code/reports/meeting notes and Notion's Roadmap + Meetings databases.
- **[Utilities](#utilities)** — standalone helpers.

### Spec authoring

| Skill | Purpose |
|---|---|
| [spec](skills/spec/SKILL.md) | Generate a multi-file engineering specification (architecture, data models, APIs, features) from a system description. |
| [spec-review](skills/spec-review/SKILL.md) | Evaluate a `specification.md` for clarity, completeness, and consistency — focused on data model correctness and Given-When-Then behavior coverage. |

### Dev flow

Three phases of a development task — **planning**, **wrap-up**, and **session housekeeping** — plus one orchestrator that ties wrap-up together.

```
   PLANNING                IMPLEMENTATION              WRAP-UP
 ┌────────────┐                                  ┌──────────────────┐
 │  discuss   │ ───►  (you write the code)  ───► │     wrap-up      │
 └────────────┘                                  └────────┬─────────┘
                                                          │ orchestrates
                                       ┌──────────────────┼──────────────────┐
                                       ▼                  ▼                  ▼
                                    verify          update-docs         code-review
                                       │                  │                  │
                                       └────────────►  report  ◄─────────────┘
                                                          │
                                                          ▼
                                                   rename-session
                                                          │
                                                          ▼
                                                    sync-report (if Notion-configured)
                                                          │
                                                          ▼
                                                  git commit (optional)
                                                          │
                                                          ▼
                                                   deploy (optional)
```

| Skill | Phase | Purpose |
|---|---|---|
| [discuss](skills/discuss/SKILL.md) | planning | Senior design/architecture advisor that drives a collaborative back-and-forth before any plan is written. Auto-invoked during plan mode. |
| [verify](skills/verify/SKILL.md) | wrap-up | Executes the implementation plan's Test plan / Verification section. **Runner, not author** — does not write new tests. |
| [update-docs](skills/update-docs/SKILL.md) | wrap-up | Detection-driven docs updater. Scans the project's doc layout, classifies the diff, and proposes per-file edits. |
| [code-review](skills/code-review/SKILL.md) | wrap-up | Multi-agent review of the local git diff. Writes a single `REVIEW.md` with findings tiered Critical/Warning/Suggestion/Nit (drops only auto-zeroed false positives). |
| [report](skills/report/SKILL.md) | wrap-up | Distills the conversation, file changes, and decisions into `docs/reports/YYYY-MM-DD-[title].md`. |
| [rename-session](skills/rename-session/SKILL.md) | housekeeping | Renames the current Claude Code session JSONL with a short title. Auto-invoked after `report` runs. |
| [wrap-up](skills/wrap-up/SKILL.md) | orchestrator | Runs `verify → update-docs → code-review → report → rename-session → sync-report → git commit → deploy` in order, stopping on the first failure. |

**How to use:**

- **Starting a non-trivial task?** Begin with `/discuss` (or just enter plan mode — `discuss` auto-invokes) to surface design alternatives before writing code.
- **Done implementing?** Run `/wrap-up`. It chains the wrap-up steps end-to-end so you don't have to remember the order or rerun them by hand. Stop and surface failures rather than pushing through.
- **Need just one step?** Each skill is invocable on its own — `/verify`, `/update-docs`, `/code-review`, `/report`, `/rename-session` — and `wrap-up` will skip steps you've already run earlier in the session if nothing relevant changed.
- **Manual flow without `wrap-up`:** `/verify` → `/update-docs` → `/code-review` → fix Critical/Warning findings (Suggestion/Nit are advisory) → `/report` → `/rename-session` → `/sync-report` → commit → deploy.

### Notion integration

These skills bridge between local code/docs and a shared Notion workspace (Roadmap DB + Meetings DB). **Notion is master** for task and meeting state; local files are working copies.

```
                ┌────────────────┐
                │  setup-notion  │  (one-time, writes config to AGENTS.md)
                └────────────────┘

 MEETING FLOW                                    TASK FLOW
 ────────────                                    ─────────
 transcript / Plaud URL                     ┌──► Notion task
       │                                    │          │
       ▼ /meeting-notes                     │          ▼ /fetch-task
 docs/meetings/YYYY-MM-DD-*.md              │    docs/tasks/<slug>.md
       │                                    │          │
       ▼ /upload-meeting                    │      (you work)
 Notion Meetings DB page                    │          │
       │                                    │          ▼ /report
       ▼ /create-tasks                      │    docs/reports/YYYY-MM-DD-*.md
 extracts commitments → Notion tasks ───────┘          │
 (links back to meeting)                               ▼ /sync-report
                                                 appends to linked Notion task
```

| Skill | Direction | Purpose |
|---|---|---|
| [setup-notion](skills/setup-notion/SKILL.md) | config | One-time wizard. Records Roadmap DB URL, Meetings DB URL, and optional team roster in `AGENTS.md`; adds `docs/tasks/` to `.gitignore`. Idempotent. |
| [fetch-task](skills/fetch-task/SKILL.md) | Notion → local | Pulls a Notion task into `docs/tasks/<slug>.md`. **Read-only against Notion.** Refreshes only the managed `# Context` section on re-run. With no args, picks from your active tasks. |
| [sync-report](skills/sync-report/SKILL.md) | local → Notion | Pushes `docs/reports/*.md` to a Notion task — appends body, suggests Status, fills Github Link from HEAD. Linked reports fast-path; unlinked reports prompt a candidate picker. |
| [meeting-notes](skills/meeting-notes/SKILL.md) | transcript → local | Turns a transcript (Plaud.ai share URL, local file, or pasted text) into a structured Traditional-Chinese meeting note at `docs/meetings/YYYY-MM-DD-<title>.md`. |
| [upload-meeting](skills/upload-meeting/SKILL.md) | local → Notion | Uploads a meeting markdown to the configured Notion Meetings DB. Auto-chained after `/meeting-notes`. |
| [create-tasks](skills/create-tasks/SKILL.md) | local → Notion | Extracts commitments from a meeting note, classifies LINK / DRAFT / SKIP, pre-matches against the Roadmap's Current view, then creates new tasks + wires up the meeting's Tasks relation on approval. |

**Authority model:** Only `/sync-report` and `/create-tasks` write to Notion. `/fetch-task`, `/setup-notion`, `/meeting-notes` are read-only against Notion (setup writes to local config only). `/upload-meeting` writes one Meetings DB page.

**How to use:**

- **First time in this repo?** Run `/setup-notion` once. It writes Roadmap + Meetings DB URLs into `AGENTS.md` and gitignores `docs/tasks/`. Skipped silently on re-run.
- **Starting work on a Notion task?** Run `/fetch-task <url>` to pull it into `docs/tasks/<slug>.md`. With no args, you get a picker of your active tasks. Re-run any time to refresh the `# Context` section without touching your notes.
- **Done with a task?** `/wrap-up` automatically chains `/sync-report` at step 6 — appends your report to the linked Notion task and suggests a Status. To run it standalone: `/sync-report` after `/report`.
- **After a meeting?** `/meeting-notes <plaud-url | file | paste>` synthesizes a structured note. It then auto-chains `/upload-meeting` (push to Meetings DB) and offers `/create-tasks` (extract commitments → Notion tasks, linked back to the meeting).

### Utilities

| Skill | Purpose |
|---|---|
| [find-session](skills/find-session/SKILL.md) | Search Claude Code session transcripts (`~/.claude/projects/`) by topic keyword or by which files were touched. Returns session UUIDs for `claude --resume`. |

## Folder Structure

```
dev-skills/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md
│       └── agents/ (optional)
│           └── <agent-name>.md 
├── AGENTS.md
├── CLAUDE.md  →  AGENTS.md (symlink)
└── README.md
```


## Install

### Claude Code (as a plugin)

From GitHub:

```
/plugin marketplace add FooJiaYin/dev-skills
/plugin install dev-skills
```

The first command registers this repo's `marketplace.json` as a plugin source; the second installs the `dev-skills` plugin from that marketplace. After install, restart Claude Code to load the skills.

For local development against a clone:

```
/plugin marketplace add ~/dev-skills
/plugin install dev-skills@dev-skills
```

### Gemini CLI

Install all skills from this repo (user-level / global):

```
gemini skills install https://github.com/FooJiaYin/dev-skills.git --path skills
```

Project-level install:

```
gemini skills install https://github.com/FooJiaYin/dev-skills.git --path skills --scope workspace
```

Or, if you've cloned the repo locally, link it for live updates:

```
gemini skills link ~/dev-skills/skills
```

Verify with `gemini skills list`, or `/skills reload` inside an active session.

### GitHub CLI (multi-agent)

The [`gh skill`](https://cli.github.com/manual/gh_skill) command can install individual skills from this repo into any supported agent:

```bash
gh skill install FooJiaYin/dev-skills <skill-name> --agent claude-code --scope user
gh skill install FooJiaYin/dev-skills <skill-name> --agent gemini-cli --scope user
gh skill install FooJiaYin/dev-skills <skill-name>                         # defaults to github-copilot, project scope
```

`<skill-name>` is one of: `code-review`, `create-tasks`, `discuss`, `fetch-task`, `find-session`, `meeting-notes`, `rename-session`, `report`, `setup-notion`, `spec`, `spec-review`, `sync-report`, `update-docs`, `upload-meeting`, `verify`, `wrap-up`. See [`gh skill install`](https://cli.github.com/manual/gh_skill_install) for the full list of supported agents and flags.

### Manual

Each `skills/<name>/` folder follows the standard Agent Skills layout (a `SKILL.md` with YAML frontmatter). Drop a skill folder into whichever directory your agent reads from:

- Claude Code: `~/.claude/skills/` (user) or `.claude/skills/` (project)
- Gemini CLI (user): `~/.gemini/skills/` or `~/.agents/skills/`
- Gemini CLI (project): `.gemini/skills/` or `.agents/skills/`
- GitHub Copilot (user): `~/.copilot/skills/` or `~/.agents/skills/` or `~/.claude/skills/`
- GitHub Copilot (project): `.github/skills/` or `.agents/skills/` or `.claude/skills/`

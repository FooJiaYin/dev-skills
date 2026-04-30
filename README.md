# dev-skills

A collection of reusable Agent Skills for software development workflows. Built for Claude Code as a plugin; the individual `SKILL.md` files are also usable by any agent that reads the Agent Skills format.

## Skills

The skills cover three phases of a development task — **planning**, **wrap-up**, and **session housekeeping** — plus one orchestrator that ties wrap-up together.

```
   PLANNING                IMPLEMENTATION              WRAP-UP
 ┌────────────┐                                  ┌──────────────────┐
 │  discuss   │ ───►  (you write the code)  ───► │     wrap-up      │
 └────────────┘                                  └────────┬─────────┘
                                                          │ orchestrates
                                          ┌───────────────┼───────────────┐
                                          ▼               ▼               ▼
                                       verify       update-docs      code-review
                                          │               │               │
                                          └──────►  report  ◄─────────────┘
                                                          │
                                                          ▼
                                                   rename-session
                                                          │
                                                          ▼
                                                  git commit (optional)
```

| Skill | Phase | Purpose |
|---|---|---|
| [discuss](skills/discuss/SKILL.md) | planning | Senior design/architecture advisor that drives a collaborative back-and-forth before any plan is written. Auto-invoked during plan mode. |
| [verify](skills/verify/SKILL.md) | wrap-up | Executes the implementation plan's Test plan / Verification section. **Runner, not author** — does not write new tests. |
| [update-docs](skills/update-docs/SKILL.md) | wrap-up | Detection-driven docs updater. Scans the project's doc layout, classifies the diff, and proposes per-file edits. |
| [code-review](skills/code-review/SKILL.md) | wrap-up | Multi-agent review of the local git diff. Writes a single `REVIEW.md` filtered by a confidence rubric (≥80). |
| [report](skills/report/SKILL.md) | wrap-up | Distills the conversation, file changes, and decisions into `docs/reports/YYYY-MM-DD-[title].md`. |
| [rename-session](skills/rename-session/SKILL.md) | housekeeping | Renames the current Claude Code session JSONL with a short title. Auto-invoked after `report` runs. |
| [wrap-up](skills/wrap-up/SKILL.md) | orchestrator | Runs `verify → update-docs → code-review → report → rename-session → git commit` in order, stopping on the first failure. |

### How to use them

- **Starting a non-trivial task?** Begin with `/discuss` (or just enter plan mode — `discuss` auto-invokes) to surface design alternatives before writing code.
- **Done implementing?** Run `/wrap-up`. It chains the five wrap-up steps so you don't have to remember the order or rerun them by hand. Stop and surface failures rather than pushing through.
- **Need just one step?** Each skill is invocable on its own — `/verify`, `/update-docs`, `/code-review`, `/report`, `/rename-session` — and `wrap-up` will skip steps you've already run earlier in the session if nothing relevant changed.
- **Manual flow without `wrap-up`:** `/verify` → `/update-docs` → `/code-review` → fix any ≥80-confidence findings → `/report` → `/rename-session` → commit.


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

`<skill-name>` is one of: `code-review`, `discuss`, `rename-session`, `report`, `update-docs`, `verify`, `wrap-up`. See [`gh skill install`](https://cli.github.com/manual/gh_skill_install) for the full list of supported agents and flags.

### Manual

Each `skills/<name>/` folder follows the standard Agent Skills layout (a `SKILL.md` with YAML frontmatter). Drop a skill folder into whichever directory your agent reads from:

- Claude Code: `~/.claude/skills/` (user) or `.claude/skills/` (project)
- Gemini CLI (user): `~/.gemini/skills/` or `~/.agents/skills/`
- Gemini CLI (project): `.gemini/skills/` or `.agents/skills/`
- GitHub Copilot (user): `~/.copilot/skills/` or `~/.agents/skills/` or `~/.claude/skills/`
- GitHub Copilot (project): `.github/skills/` or `.agents/skills/` or `.claude/skills/`
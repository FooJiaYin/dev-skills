## Python
1. Before running python code, check if virtual environment (`env`/`.venv`) exists
2. If exists, `source .venv/bin/activate` (Linux/Mac) or `source .venv/Scripts/activate` (Windows)

## Node.js
1. Use `yarn` instead of `npm`, unless `pnpm` is specified

## Documentation
1. Use `docs` folder for documentation files
2. Use `AGENTS.md` for agent-related documentation, instead of `CLAUDE.md`, `CURSOR.md`, etc. Add symlink of `AGENTS.md` as `CLAUDE.md` for backward compatibility but prefer `AGENTS.md` for all updates.
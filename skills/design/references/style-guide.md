# Style guide (one per direction)

Write one before building each direction; its builder gets only its own guide and references. Worked example: [styles/dark-glassmorphism.md](styles/dark-glassmorphism.md).

1. **Name** — the known style name and aliases, with where it came from (a row in `styles/index.md` or `styles/ui-ux-pro-max-styles.csv`). No invented names.
2. **References** — 2–3 real examples you found: file path or link, and what is visible in each. Keep observations apart from the tokens you suggest.
3. **Tokens** — one table: composition / layout, background, container material, font, type scale, text colour, border, radius, spacing, shadow, blur / effects, icon, selection state, accent colour. Values are starting points, not measurements.
4. **Applied to this product** — how the key screen is composed in this style (what fills the stage, where the main content, tools and secondary panels sit). This section stays in the project, never in the library.
5. **Failure and check** — the usual way this style goes wrong and one check that catches it (e.g. glass with nothing behind it to show through).

## Side-by-side table

After all guides, one table (in chat, not on the page) with one row per direction and these columns: how the screen is organised, where edges come from, radius character, icon treatment, selection treatment, visual lead. No two rows may share how the screen is organised — the same layout with a different material is one direction, not two.

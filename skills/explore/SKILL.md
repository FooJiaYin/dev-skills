---
name: explore
description: Build several distinct design or prototype versions for the user to choose between, then narrow, combine and complete the chosen ones. Use when the user asks for "N 個版本給我選", "做幾個方向", "給我幾版看看", "explore options", or wants to compare visual directions / layouts before committing to one.
---

# explore

1. **Settle the axes first** with one question: what should the versions differ in, and how complete each should be. If the user says "you decide", vary **layout and presentation as well as style** — each version takes its own concept or reference. Versions that only swap colours and fonts on one layout get sent back.
2. **Build only what shows the difference**: the most characteristic sections plus shared chrome (nav, CTAs, loader), not the whole site. Put shared behaviour in one common file so versions differ in presentation, not in bugs.
3. **Check every version** at desktop and phone widths before showing it (`headless-shots` `steps.mjs`: scroll / hover steps, no horizontal overflow). Fix what the screenshots show.
4. **Make it viewable where the user is**: an index page linking every version, published to one preview URL (Artifact) that stays the same across rounds — a localhost link is useless over Remote Control.
5. **Report each round as one table**: version → concept → layout → signature interaction, plus anything that departs from the spec or adds copy the source doesn't have.
6. **Narrow**: when the user picks or combines, build the combination as a new version, keep the chosen ones, and move the rest to `_archive/` (never delete). For full builds of several chosen versions, write one shared content brief and fan out one agent per version; verify each at integration.

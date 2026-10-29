# Review checklist

Check in this order. A pretty version makes reviewers forgive usability problems, so visual comes last and never offsets an earlier failure.

| Pass | Check |
|---|---|
| Flow | Every acceptance criterion in `brief.md` can be completed, including its exceptions (empty data, invalid input, no permission, going back) |
| Usability | Nielsen's 10 heuristics; controls look like what they do (signifiers) and move the way they read (mapping); few choices per step (Hick); primary targets large and close (Fitts) |
| Accessibility | Text contrast ≥ 4.5:1, keyboard reachable, visible focus, reduced motion respected, no horizontal scroll on phone |
| Brand | Each rule in `brief.md` passes or fails individually |
| Visual | Clear hierarchy, consistent spacing and grid, the named peak moment actually lands |
| Distinctness | Swap the headlines between two versions — if nobody would notice, they are too similar; any two differ on ≥ 3 axes |

Mark each item pass / fail / can't verify, with the screenshot it rests on. Report separately what you saw in the browser, what you only read in code, and what you didn't test.

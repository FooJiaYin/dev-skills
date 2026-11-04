# Review commons

Shared by `quick-review`, `code-review` (standards agent) and the future `pr-review`.

**This is a floor, not the scope.** Finish your own review first, using your own judgment. Then use this list only to catch what you missed. Do not drop a finding because it is not listed here.

A project may add `docs/review-standard.md`; it is read after this file and wins on conflict.

## 1. Comment rules

- Comment only on lines the change touched (`+` / `-`). Do not report issues that existed before the change.
- Each finding states the trigger: the input or state, and what goes wrong.
- Be declarative. No "please verify / check / ensure" comments: name a concrete problem or say nothing.
- Severity: Critical / Warning / Suggestion / Nit.
- Ignore style unless it obscures meaning or breaks a standard below.
- Don't explain the code back to its author. One issue per finding; list duplicate locations on one line.

## 2. Basic standards

- Reuse existing utilities, components and patterns before adding new ones.
- New UI text matches the language of the sibling strings in the same file or component, not the chat language.
- No internal shorthand (source codes, question numbers, invented field names) in user-facing text.
- Derived status from a variable-size input handles the empty / zero case explicitly; an empty collection resolves to the terminal state, not "in progress".
- Size and count constraints are validated at the authoritative choke point (server action / RPC), not only by a UI default.
- When the same state is derived in two places (optimistic client and server rebuild), a guard added to one is mirrored in the other.
- Temporary artifacts (screenshots, measurement pages, drafts) are not written into the repo.
- Bulk DB writes, deletes and migrations come with a preview or guard on the affected rows.

## 3. Security checklist

- Hard-coded secrets, tokens or keys; `.env` or credential files added to the commit.
- SQL, shell-command or path injection; queries built by string concatenation.
- Authorization: missing permission checks; RLS / policy changes that widen access.
- XSS: `dangerouslySetInnerHTML`, `innerHTML`, unescaped user content in output.
- Server-only values reachable from the client (service-role keys, server env vars, admin endpoints).
- Permissive CORS, insecure cookie flags, open redirects.
- `eval`, `new Function`, unsafe deserialization of untrusted input.

## Added by /improve

<!-- /improve appends rules here: one line each, with source and date. -->

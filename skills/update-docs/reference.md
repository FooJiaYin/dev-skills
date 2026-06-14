# Docs layout & naming reference

A reference layout the `update-docs` skill consults **when proposing a new doc file**. Not a mandate — projects may use none, some, or a variant of this. **Existing project structure always wins**; this reference only seeds defaults when there's no existing precedent to follow.

## Shared / top-level `docs/`

```
docs/
  architecture.md              # stack, diagram, deployment, folder structure
  features/
    index.md
    [feature].md
  schemas/
    index.md                   # ERD + relations overview
    [entity].md                # per entity: fields, constraints, lifecycle
  setup.md                     # dev environment setup
  deploy.md                    # deployment, environments, CI/CD
  testing.md                   # testing strategy + how-tos
  design.md                    # design tokens, shared components
  TODO.md                      # known gaps, tech debt, future work
  spec/                        # frozen planning docs — do not edit post-implementation
```

## Backend-repo `docs/`

```
backend/docs/
  schemas/
    index.md
    [entity].md
  api/
    index.md                   # endpoint table
    [resource].md              # grouped by resource (auth.md, users.md, …)
  services/      [optional]    # cross-cutting logic spanning multiple endpoints
  cron/          [optional]    # scheduled tasks
  workers/       [optional]    # queue consumers
  events/        [optional]    # event handlers
```

## Frontend-repo `docs/`

```
frontend/docs/
  architecture.md              # routing, bundle strategy, toolchain
  conventions.md               # FE patterns, data access, formatting, a11y, linting
  state.md                     # global state strategy
  pages/
    index.md                   # sitemap / route table
    [page].md                  # route, data deps, state, components, a11y
  components.md                # shared component catalog
```

## Notes

- Per-entity / per-resource / per-page folders pair with an `index.md` that's the overview (ERD, endpoint table, sitemap). Always update the index alongside any per-file change.
- `spec/` is frozen at implementation start. Living docs go in the surrounding `docs/`.
- Orgs forking this plugin may rewrite this file to match their own layout.

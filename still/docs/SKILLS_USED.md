# Skills installed and applied

Six GitHub repositories were vendored into `_skills/` at the workspace root.
They contain 86 `SKILL.md` files and 1,330 files in total. Git and raw GitHub
endpoints returned 403 in this environment, so the repos came through the
codeload tarball endpoint. The copies are real upstream trees, not summaries.

| Repository | Local path | What was used |
| --- | --- | --- |
| `anthropics/skills` | `_skills/anthropics-skills/` | `skill-creator` and `web-artifacts-builder` for report-shape conventions |
| `mattpocock/skills` | `_skills/mattpocock-skills/` | `improve-codebase-architecture`, `codebase-design`, `grill-with-docs`, `tdd`, `code-review` |
| `vercel-labs/agent-skills` | `_skills/vercel-agent-skills/` | `writing-guidelines` for the README and docs |
| `vercel-labs/skills` | `_skills/vercel-skills-tool/` | skill packaging and distribution conventions |
| `obra/superpowers` | `_skills/obra-superpowers/` | `brainstorming`, `verification-before-completion`, `receiving-code-review` |
| `tomerose/stop-slop` | `_skills/stop-slop/` | the writing standard in `WORKFLOW.md` Section 6 |

## Procedures that materially shaped the program

- **`scientific-brainstorming`** and **`scientific-critical-thinking`** (built-in): the ideation register in `brainstorm/session.json`, the pre-declared criteria in `criteria.json`, the weighted matrix and the adversarial review. Cited in `PLAN.md` References.
- **Brainstorming**: independent idea generation before evidence check, provenance labels, preserved dissent, and one reopened generation round after the prior-art survey.
- **Verification before completion**: no gate closes on a self-report. Every round in `REVIEW_LOG.md` shows fresh command output.
- **TDD / code review**: tests were written against public interfaces; the boss sent ten rounds of work back rather than accepting them.
- **improve-codebase-architecture**: the ranked candidates, deletion test, before/after diagrams in `architecture-review.html`, and the C1 deepening into `evidence.py`.
- **codebase-design**: the vocabulary in `GLOSSARY.md` and `CONTEXT.md` (module, interface, depth, seam, adapter, leverage, locality).
- **grill-with-docs**: the design tree in `PLAN.md` Section 5 and the inline grilling loop in the architecture report.
- **stop-slop** and **writing-guidelines**: no throat-clearing openers, no binary-contrast templates, no filler adverbs, no em dashes, active voice, specific claims.

## What "installed" means here

The vendored repos are available offline in this workspace. The skill procedures
were applied as working methods during design, implementation, review and the
architecture pass. They were not registered as runtime plugins, and `still`
itself has no skill dependency: the shipped program is a standalone,
zero-runtime-dependency Python CLI. A reader who wants to re-run a procedure can
open the corresponding `SKILL.md` in `_skills/`.

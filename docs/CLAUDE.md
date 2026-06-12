# docs/ — Context for Claude

> **Tree position:** `/ (root) → docs/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for project-wide rules and architecture.

---

## What this directory is

`docs/` is the MkDocs source tree, published via GitHub Actions to GitHub Pages.
Every `.md` file here maps 1:1 to a page in the site via `mkdocs.yml`.

---

## File map

```
docs/
├── CLAUDE.md                ← this file (not published — excluded from mkdocs nav)
├── index.md                 ← landing page: pipeline overview + topic list
├── visao_produto_projeto.md ← full product/project vision (stakeholders, objectives, SE strategy)
├── requisitos.md            ← functional (RF01–RF10) and non-functional (RNF01–RNF07) requirements
├── backlog.md               ← user stories (US01–US14), prioritization, MVP, acceptance criteria
├── cronograma.md            ← 4-wave schedule with milestones and risk notes
├── arquitetura.md           ← pipe-and-filter diagram, filter contracts, I/O file map, design decisions
└── contributing.md          ← git workflow, running filters, coding standards, definition of done
```

---

## MkDocs nav (mkdocs.yml)

```yaml
nav:
  - Início: index.md
  - Visão do Produto e Projeto: visao_produto_projeto.md
  - Requisitos: requisitos.md
  - Backlog: backlog.md
  - Cronograma: cronograma.md
  - Arquitetura: arquitetura.md
  - Contribuição: contributing.md
```

Do not rename files without updating the nav. Do not add pages without adding a nav entry.

---

## Content ownership and update rules

| File | Owner trigger | When to update |
|------|--------------|----------------|
| `index.md` | Any pipeline change | When a module is added, renamed, or reordered |
| `visao_produto_projeto.md` | Strategic or team decisions | When scope, team, or SE strategy changes |
| `requisitos.md` | Requirement changes | When RF/RNF are added, removed, or revised |
| `backlog.md` | Sprint / wave planning | When user stories are added, split, or acceptance criteria change |
| `cronograma.md` | Timeline changes | When wave dates shift, milestones are added, or completion status changes |

---

## Writing conventions

- Language: **Portuguese** — all user-facing content (headings, tables, prose)
- File names: **snake_case**, `.md` extension
- Every page must have a single `#` H1 matching the nav label
- Revision history table at the bottom of each page: `| Data | Versão | Descrição | Autor |`
- Do not use emojis
- Do not add `CLAUDE.md` to the mkdocs nav

---

## Critical constraints inherited from root

- Deadline for last GitHub commit: **22/06/2026**
- Do not commit directly to `main` — use branches and PRs
- All doc filenames use relative paths; never hardcode absolute paths in links

# 🗺️ AXIS-NAVIGATOR
### Semantic Knowledge Graph for the PureDhamma Corpus

> **Part of the AXIS-NIDDHI Ecosystem** — `@matikamata`

AXIS-NAVIGATOR is the semantic navigation layer for the PureDhamma corpus. It solves the "link rabbit hole" problem: instead of clicking through an endless chain of prerequisite posts, the Navigator guides the student along a curated, concept-anchored learning path.

## Core Invariant

> *"The Navigator never creates knowledge. It maps paths through existing canonical knowledge."*

All concept nodes are grounded in **CSL entry IDs** from the [axis-niddhi](https://github.com/matikamata/axis-niddhi) corpus (748 posts, 202 translated to pt-BR as of v1.0.0).

---

## Architecture

```
axis-navigator/
├── semantic/
│   ├── concepts/        ← 11 canonical Pāli concept JSONs
│   │   ├── anicca.json
│   │   ├── anatta.json
│   │   ├── dukkha.json
│   │   ├── nibbana.json
│   │   └── ... (11 total)
│   └── concept_schema.json   ← JSON schema for concepts
│
├── navigator/
│   ├── concept_map.json      ← Semantic graph (10 nodes, 35 edges)
│   ├── concept_index.json    ← Full concept index
│   ├── cosmos_graph.json     ← Universe-level graph data
│   ├── graph_builder.py      ← Graph construction engine
│   └── generate_concept_map.py
│
├── paths/
│   ├── learning_paths.json   ← 3 curated learning paths (Beginner→Advanced)
│   ├── study_paths.json      ← Sequential study path definitions
│   └── cosmos_engine.py      ← Path traversal engine
│
└── ui/
    ├── start.html            ← Entry point
    ├── concepts.html         ← Concept browser
    ├── paths.html            ← Learning path viewer
    └── concept_*.html        ← Individual concept pages
```

---

## The 3 Learning Paths

| Path | Level | Concepts Covered |
|---|---|---|
| **Three Marks of Existence** | Beginner | dukkha → anicca → anatta → tilakkhana |
| **Dependent Origination** | Intermediate | avijja → sankhara → tanha → paticca_samuppada |
| **Path to Liberation** | Advanced | magga → phala → nibbana |

---

## Concept Graph (10 nodes, 35 edges)

Each concept node contains:
- `pali` — Canonical Pāli spelling
- `label` — Translation in `en` and `pt-BR`
- `type` — `dhamma_characteristic`, `doctrine`, `practice`, `attainment`, `mental_factor`
- `edges` — Dependent concepts
- `csl_entries` — Canonical citations (PD#PN + slug)

---

## Ecosystem

| Repository | Role |
|---|---|
| [axis-niddhi](https://github.com/matikamata/axis-niddhi) | Core SSG — bilingual static site |
| **axis-navigator** ← you are here | Semantic graph + learning paths |
| axis-nana *(coming soon)* | Knowledge Q&A engine |
| axis-preservation *(coming soon)* | Integrity seals + IPFS distribution |

---

## Live Showcase

🌐 **https://niddhi.netlify.app**

Original corpus: **https://puredhamma.net** (Prof. Lal Dhammajoti, Ph.D.)

---

*AXIS-NIDDHI Ecosystem — Deadline: 2222 CE* 🛸

Scan the current project: `{project}`

Your task is to generate (or update) a `CLAUDE.md` for this novel project, providing future Claude sessions with quick project context for continuation writing.

This file is a **continuation navigation document**, not a complete project archive:
- Output: 1500–2500 characters, hard cap 3000 characters.
- Keep only information essential for future continuation: project identity, current progress, story state, writing rules, and key taboos.
- Do not copy long setting texts, full summaries, complete character profiles, or log content — only cite key conclusions.
- If content is too much, prioritize compressing background recap and finished early details. Keep current state, open hooks, character relationship status, and style rules.

## Reading Priority

Scan in this order; earlier files have priority:

1. `.project_info.json` — project metadata (genre, scale, progress, act count, chapter count)
2. `03_state/Story_Summary.md` — the story's narrative thread to date (if it exists)
3. `03_state/State_v*.md` (latest one) — current scene freeze, relationship pressure, foreshadowing state, rhythm state
4. `04_characters/Character_Profiles.json` + `Relationship_Matrix.json` — core character identity and current relationship
5. `00_baseline/Story_Axis.md` + `Act_Framework.md` — story's overall design
6. `00_baseline/Core_Skeleton_*.md` — each act's structure
7. `00_baseline/Worldbuilding.md` — world rules
8. `00_baseline/Creative_Proposal_*.md` + style suggestions — style foundation

Skip files that don't exist (during the post_05b phase there are no drafts or state documents — this is normal).

## Output Structure

Strictly output the following sections; each section only writes key conclusions, no exposition:

```markdown
# {project_name} — Project CLAUDE.md

## 1. Project Identity

- Genre:
- Scale: (Short / Medium / Long / Serial, target character count)
- Language:
- Reference Works:

## 2. Story Synopsis

In 3–5 sentences summarize the story's core premise, main conflict, and emotional core. No more than 200 characters.

## 3. Current Progress

- Completed: Act X, Chapter Y (`Draft_v{n}.md`)
- Current act arc position: (buildup / escalation / turn / climax / fall)
- Remaining chapters:

(Fill "Structure planning complete, prose not yet started" during the post_05b phase)

## 4. Core Character Status

2–3 lines per main character: current situation, core desire, core fear, current relationship with other characters. No more than 4 characters.

## 5. Relationship Map

Describe current relationship state in the most concise way (who-to-who, what stage, what tension). Can use list or compact table.

## 6. Open Hooks

List currently unresolved hooks (foreshadowing, relationship debts, unfulfilled promises, unrevealed truths), one sentence each, with source chapter annotated.

## 7. Style Rules

Core style constraints distilled from the creative proposal and existing prose (sentence preferences, register, rhetorical density, emotional texture, narrative POV). 5–8 items, one sentence each.

## 8. Key Taboos

Customized taboos for this project (not general writing common sense). 3–5 items, each explaining "what is forbidden" and "why it is especially important for this project."
```

## Update Principles (post_17 phase)

If `{project}/CLAUDE.md` already exists (meaning this is not the first generation):
- Keep style rules and key taboos that are still valid from the previous version
- Update progress, character status, relationship map, and open hooks to the latest state
- Delete foreshadowing already recovered and relationship debts already settled
- Do not bloat the document during updates — if new content causes the length to exceed the limit, compress early completed details

Write to absolute path: `{project}/CLAUDE.md` (project root, same level as `.project_info.json`, not inside any subdirectory).

Read: `{baseline}/Story_Axis.md`

Read: `{baseline}/Act_Framework.md`

Read: `{baseline}/Core_Skeleton_{act_num}.md`

Read: `{quality}/Act_Skeleton_Appeal_Review_{act_num}.md` (if it exists)

Read: `{quality}/Act_Skeleton_Rewrite_Notes_{act_num}.md` (if it exists)

Read: `{baseline}/Worldbuilding.md`

Read: `{chars}/Character_Profiles.json`

Read: `{chars}/Relationship_Matrix.json`

Read: `{state}/State_v{round-1}.md` (previous chapter state document, if it exists; ignore for Chapter 1)

Read: `{plots}/Plot_v{round-1}.md` (previous chapter plot, if it exists; ignore for Chapter 1)

Read: `{quality}/Plot_Hook_Ledger.md` (if it exists)

Read: `{evolution}`

Read: `{baseline}/Creative_Proposal_{option_index}.md`

You are the context editor for a long-form serialized novel. Your task is not to generate plot. Your task is to create a lightweight, accurate, directly usable "chapter context pack" for Chapter {round}.

This step exists so that the later plot design, review, writing guide, drafting, quality review, and rewrite steps can read this file first instead of repeatedly reading the Story Axis, Act Framework, Core Skeleton, Worldbuilding, Character Profiles, and Relationship Matrix.

## Core Principles

1. Extract only the information this chapter needs. Do not produce a setting encyclopedia.
2. Preserve content that affects this chapter's character choices, conflicts, intimacy boundaries, foreshadowing, and chapter-end hook.
3. Remove history, background, character labels, and worldbuilding explanation unrelated to this chapter.
4. Character information must be "executable current state", not a static biography.
5. Relationship information must state the current distance, debt, misunderstanding, defense, attraction, and boundary.
6. If something is uncertain, write "unknown / to be confirmed this chapter" rather than invent facts.
7. Do not evaluate upstream content, do not change settings, do not add major facts.

## Output Control

- Keep the total within 1500–2500 characters, hard cap 3000 characters.
- Each subsection should keep only information useful for this chapter.
- Use short sentences and bullets. Avoid long explanations.
- You may cite filenames, but do not copy long passages.
- If content is too much, prioritize: chapter position, relevant characters, relationship debts, open hooks, hard constraints, and usable scene objects.

## Required Output

Write to: `{chapter_context}`

## Output Format

```markdown
# Chapter Context Pack v{round}

Genre: {genre}
Description: {user_description}

## Chapter Position

- Act: Act {act_num}
- Chapter: Chapter {round}
- This chapter's function in the Story Axis:
- This chapter's position in the current act's Core Skeleton:
- State of the previous chapter that this chapter must inherit:
- Subsequent content this chapter must not consume in advance:

## This Chapter's Core Constraints

- Mainline constraint:
- Act constraint:
- Worldbuilding / rule constraint:
- Character relationship constraint:
- Do not break:

## Relevant Character Slices

### [Character Name]

- Current situation:
- Current goal:
- Current pressure:
- Hidden desire:
- Fear / concern:
- Visible behavioral tendency:
- Speech and action characteristics:
- Change this chapter can push:
- Points this chapter must not drift away from:

## Relationship Slices

### [Character A] / [Character B]

- Current surface relationship:
- Current real relationship:
- Unpaid relationship debt:
- Defense points:
- Attraction points:
- Intimacy boundary:
- Allowed intimate acts to advance:
- Lines that cannot be crossed:
- Afterecho that must remain after advancement:

## World and Scene Slices

- Locations relevant to this chapter:
- Rules relevant to this chapter:
- Usable objects / props:
- Usable sensory anchors:
- Background pressure that cannot be forgotten:

## Hook and Foreshadowing Slices

- Hooks from the previous chapter that must be inherited:
- Hooks this chapter is advised to advance:
- Foreshadowing this chapter can recover:
- New debts this chapter should open:
- Long-term issues暂不处理 but cannot be forgotten:

## Theme Slice

- Core question (from theme_state):
- Protagonist's current stance:
- This chapter's theme task (touch / destabilize / deepen / reverse which aspect of the core question):

## Imagery Slice

- Core imagery this chapter can use (from symbol_state active_symbols):
- Current semantic meaning and this chapter's expected usage (strengthen / reverse / first appearance):

## Subplot Slice

- Active subplots this chapter (from subplot_state active_subplots):
- Subplot beats this chapter should advance:
- Dormant subplots that have been ignored too long (warning, from dormant_subplots):

## Reader Knowledge Slice

- Key facts the reader currently knows (from known_truths):
- Current false beliefs (from false_beliefs):
- This chapter's information release plan (what to reveal / what to preserve / what to misdirect):

## Style and Prose Execution Hints

- This chapter's recommended rhythm position (from rhythm_state):
- This chapter's suitable emotional texture:
- Previous two chapters' opening / conflict types (infer from previous state, previous plot, and existing drafts for anti-repetition):
- Prose degeneration this chapter should avoid (infer from the writing guide, creative constitution, and problems visible in existing drafts):
- High-risk degeneration this chapter:
- Key points for downstream steps reading this file:
```

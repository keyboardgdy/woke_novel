Read: `{baseline}/Story_Axis.md`

Read: `{quality}/Story_Axis_Appeal_Review.md`

Read: `{quality}/Story_Axis_Rewrite_Notes.md` (if present)

Read: `{baseline}/Creative_Proposal_{option_index}.md`

Read: `{baseline}/Worldbuilding.md`

Read: `{chars}/Character_Profiles.json`

Read: `{chars}/Relationship_Matrix.json`

Based on `Story_Axis.md`, select an appropriate macro-structure model and perform professional act planning — cutting the macro skeleton into executable structural units.

---

## Design Principles

Act planning is **rhythm architecture**. Each act is a complete pressure cycle: accumulation → escalation → eruption → aftermath. Acts are not laid flat next to each other; they are a staircase — each act ends at a higher baseline than the last.

Good act division standards:
- Each act has its own independent core conflict (not a simple repetition of the book's core conflict)
- Each act end must have an "irreversible change" — unable to return to the previous act's state
- Adjacent acts have significantly different emotional color temperatures (not steady progression)
- Removing any act would break the logic chain of subsequent acts

---

## Output Constraints

- Each act only covers structural function, core conflict, chapter budget, character/relationship change, and end-of-act hook
- Do not expand into per-chapter plot, do not write prose scenes, do not restate the full Story Axis
- Do not pile up structural jargon to "look professional" — each item must have concrete content

---

## 1. Macro-Structure Model

Select the most suitable structure model for this story's traits (three-act / hero's journey / multi-act spiral / dual-line interweaving / other), and explain the reasoning:
- Why is this structure suited to this story?
- How does this structure serve the core conflict's escalation rhythm?

## 2. Length and Chapter Budget

Target book length: {novel_size}, target total character count: {target_word_count}.

Chapter allocation rules:
- Target single-chapter prose length: 2500–4500 characters, default around 3000 characters
- First back-calculate the total chapter count for the whole book from the target total character count, then distribute across acts
- Each act's chapter count is determined by content complexity, conflict level, and character-arc depth
- The sum of all acts' chapters must support the target total character count
- Climax acts / relationship-turn acts may add chapters; transition-and-fall acts should be compressed
- Every act must be annotated with: estimated chapter count, estimated character-count range, and the reason for the length

## 3. Act Detailed Planning

Each act contains:

| Element | Content |
| --- | --- |
| Act number and name | Verb-phrase naming (e.g., "shattering trust" not "Act Two") |
| Structural function | This act's position in the book's overall rhythm (buildup / escalation / turn / climax / settling) |
| Core conflict | This act's independent contradiction — what is its relationship to the book's core conflict |
| Entry state | What problem / pressure does the character bring into this act |
| Exit state | What irreversible change does the character leave this act with |
| Relationship stage | The core relationship is at: guarded / misunderstood / forced closer / tentative / dependent / ruptured / rebuilt / acknowledged |
| Relationship debt | Which debt does this act push forward or deepen, and why it cannot be fully settled within this act |
| Intimacy motif | Abstract intimate behaviors suitable for recurring use in this act (clothing / wounds / rainy nights / shared objects / averted gazes…) |
| End-of-act hook | Event-level suspense + relationship-level aftertaste / gap (both required) |
| Estimated chapter count | N chapters (with reasoning) |

## 4. Rhythm Design

Cross-act rhythm planning:
- Tension curve: which acts are high-pressure, which are breathing room, where are the inflection points
- Information release rhythm: how many times the core secret/truth is revealed, how much each reveal covers
- Emotional color temperature change: the temperature difference between adjacent acts (cold→hot / dark→bright /压抑→release)

## 5. Character Arc Planning

The protagonist's and core characters' change trajectories across acts:
- What core cognition/state change occurs in each act
- What the triggering event is (not specific plot, but triggering type)
- The direction of the character's arc across the book: what kind of person they start as and what kind they end as, and what the cost is

## 6. Foreshadowing and Suspense Design

- Long-term foreshadowing: planted in which act, recovered in which act, what cognitive state readers should be in during middle acts
- Short-term suspense: how suspense within each act接力 (when the last one solves, the next one has already emerged)
- Misleading design: which information deliberately lets readers form wrong expectations, and where it breaks

## 7. Timeline Design

- In-story time span: how much time the whole book covers
- Per-act time density: how many days/weeks/months this act covers, the pace
- Time-jump points: whether there are time jumps between acts, and what needs to be explained after the jump

---

【Output Format Requirement — Must Be Strictly Followed】

The document must contain the following exact marker (used for pattern matching to extract the act count). Output in original format:

```
Total Acts: N Acts
```

Write to: `{baseline}/Act_Framework.md`

Output path: `{baseline}/Act_Framework.md`

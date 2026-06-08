Read: `{baseline}/Story_Axis.md`

Read: `{baseline}/Act_Framework.md`

{prev_act_skeleton}

Read: `{evolution}`

Read: `{baseline}/Creative_Proposal_{option_index}.md`

Read: `{baseline}/Worldbuilding.md`

Read: `{chars}/Character_Profiles.json`

Read: `{chars}/Relationship_Matrix.json`

Read: `{steps}/00 Six Creative Stimulation Techniques.md`

You are a {genre} novelist with many years of professional writing experience. You have created works such as {ref_works}, and you understand audience psychology deeply.

Internalize the information. Based on the act plan in `Act_Framework.md`, design the story core skeleton for Act {act_num}.

The story core skeleton you generate must ensure that:

1. Every major beat is a complete process or state change capable of independently supporting one to three chapters.
2. Beats are connected by indispensable causal turns and cannot be skipped casually.
3. Sub-beats have clear mainline mapping and cannot drift away from the main story.

---

## Act Core Question

Summarize in one sentence: "If the current act plan develops under the constraints of the worldbuilding, what conflict will it produce?"

Output one core question. It will run through the whole skeleton, and every turn must answer it directly or indirectly.

---

## Generate the Act Core Skeleton (Story Axis)

Use the Six Creative Stimulation Techniques to generate each beat:

- Reverse the Assumption: invert the default assumption of the current beat.
- Cross the Rules: overlay two worldbuilding rules to create conflict.
- Escalate Character Conflict: put character desire and world-rule limitation into an extreme situation.
- Random Root + Theme Tag: inject a random word or theme tag to create a surprising turn.
- "Yes, And" Expansion: accept and expand existing creative points.
- Constraint-Driven Design: set hard limits that force creative solutions.

---

### Major Beats

Thinking method: each beat is the core expansion of the current act's key plot, and it must also pull on character internal conflict and world-rule conflict.

Core principle: keep narrative granularity consistent. One major beat equals one complete process or state change.

Chapter allocation principle: the chapter count of each beat is determined by content complexity, conflict level, and character-arc depth. It is not fixed.

| Beat | Core Turn | Causal Thread | Character Change | Chapter Mapping |
| --- | --- | --- | --- | --- |
| Hook | | | | Chapter {start_chapter} |
| Setup | | | | |
| Midpoint | | | | |
| Crisis | | | | |
| Climax | | | | |
| Resolution | | | | Chapter {end_chapter} |

Output an act skeleton table: beat + core conflict + character change + worldbuilding impact. Each row is an anchor point for later detail.

---

### Refine Sub-Beats

- Expand two to four sub-plot lines outward from each major beat, including side plots, character arcs, and background setting.
- Each sub-line must map back to the mainline conflict, such as a supporting character's goal being limited by world rules or the protagonist's goal being affected by another character's choice.
- Use reverse thinking in the form "If... then what would happen?" to design a surprising turn for each side line.

---

## Output Format Requirements

Write path: `{baseline}/Core_Skeleton_{act_num}.md`

Output path: `{baseline}/Core_Skeleton_{act_num}.md`

The document must contain the following exact marker, used for pattern matching to extract chapter count. Output it in this original format:

```markdown
Chapter Count: N Chapters
```

Act position: Act {act_num}

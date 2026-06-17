Read: `{baseline}/Story_Axis.md`

Read: `{baseline}/Act_Framework.md`

Read: `{quality}/Act_Framework_Appeal_Review.md`

Read: `{quality}/Act_Framework_Rewrite_Notes.md` (if present)

{prev_act_skeleton}

{prev_act_quality}

Read: `{evolution}`

Read: `{baseline}/Creative_Proposal_{option_index}.md`

Read: `{baseline}/Worldbuilding.md`

Read: `{chars}/Character_Profiles.json`

Read: `{chars}/Relationship_Matrix.json`

Read: `{steps}/00 Six Creative Stimulation Techniques.md`

You are a {genre} novelist with many years of professional writing experience. You have created works such as {ref_works}, and you understand audience psychology deeply.

Based on Act {act_num} in the Act Framework, design the act's core skeleton — splitting the act plan into a node sequence that can directly support chapter creation.

---

## Design Principles

The core skeleton is this act's "construction blueprint." Each node corresponds to 1–3 chapters of content; subsequent chapter creation receives tasks directly from here.

**Standards for a good skeleton**:
- Every node is a complete "state change" — the world entering and the world leaving are different
- Nodes are causally welded — removing any one breaks the logic of subsequent nodes
- It is not just "events happening," but "characters are forced to make choices, choices produce costs, costs change the situation"
- Main plot and emotional line advance simultaneously at every node (not alternating)
- Nodes in the first half plant unavoidable consequences for the second half

**Creative stimulation**: For each node, use the Six Creative Stimulation Techniques (reverse assumption / cross rules / escalate character conflict / random word root / Yes-And expansion / constraint-driven) to检验 — is the current design the most obvious trope? If yes, try at least one reversal or constraint-driven approach to find a more tense alternative.

---

## Length Constraints

- Target book length: {novel_size}, target total character count: {target_word_count}
- This act's chapter count must inherit the length plan from the Act Framework
- Target single-chapter prose: 2500–4500 characters, default around 3000 characters
- Each node covers 1–3 chapters, determined by content complexity (not rigidly fixed)
- Do not reduce chapter count to hit a node count, and do not cram multiple complete turns into the same chapter
- Each chapter carries only one core dramatic change

---

## Output Structure

### 1. Act Core Question

One sentence: What is this act's core conflict? All nodes respond to this question.

Format: "When ______ (situation), ______ (character) must choose between ______ and ______, and the cost of this choice is ______."

### 2. Mainline Node Table (Major Beats)

Each node contains:

| Element | Content Requirement |
| --- | --- |
| Node name | Verb phrase (e.g., "choosing silence" not "the silence incident") |
| Core turn | What irreversible change occurs — what is the essential difference between before and after |
| Causal thread | Front: what setup caused it to erupt now? Back: where do its consequences point to the next node? |
| Character choice | What decision is the character forced to make here? What did they give up? |
| Character state change | How has internal cognition / belief / self-positioning shifted |
| Relationship change | How the core relationship's distance / trust / debt / intimacy boundary shifted |
| Chapter mapping | Chapter X–Y (explain why so many/few chapters are needed) |

Node count suggestions:
- Short acts (3–5 chapters): 4–5 nodes
- Medium acts (6–9 chapters): 5–7 nodes
- Long acts (10+ chapters): 6–8 nodes

**Note**: Do not mechanically apply Hook/Setup/Midpoint/Crisis/Climax/Resolution templates. Design flexibly based on this act's position and function in the book — a transition act may not have a Climax; a climax act may have multiple Crises. Node names should reflect concrete content, not structural terminology.

### 3. Sub-Beats

Expand 2–4 sub-lines from each mainline node:

Each sub-line must satisfy:
- Clearly mapped to the mainline conflict (how does the supporting character's choice affect the protagonist's predicament)
- Has its own small causal闭环 (not a floating decoration)
- At least one contains information gap / misjudgment (providing soil for later reversals)

Sub-beats are not complete subplot designs — just clarify: who, does what, how it pulls the mainline. Each is 1–2 sentences.

### 4. Emotional Rhythm Line

The temperature curve of this act's core relationship:
- Starting temperature: the relationship distance when entering this act
- Key push points: which nodes approach the intimacy boundary
- Retreat points: which nodes pull back due to fear / misjudgment / external pressure
- Exit temperature: is the relationship closer or farther when leaving this act compared to entry, and what is the cost
- This act's intimacy motif: concrete actions / objects / distances suitable for recurring use (inherited and refined from the Act Framework)

### 5. Foreshadowing Layout

- Foreshadowing this act inherits: which lines from previous acts/skeleton need to be advanced or recovered in this act
- New foreshadowing this act plants: concrete carriers (object / dialogue / detail action), disguise degree (obvious at a glance / noticeable on reflection / fully hidden)
- End-of-act suspense: one gap each at the event layer and the relationship layer

---

## Output Format Requirements

Write path: `{baseline}/Core_Skeleton_{act_num}.md`

The document must contain the following exact marker (used for pattern matching to extract the chapter count). Output in original format:

```markdown
Chapter Count: N Chapters
```

Act position: Act {act_num}

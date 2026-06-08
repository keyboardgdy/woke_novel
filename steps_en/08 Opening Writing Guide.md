Read: `{plots}/Plot_v1.md`

Read: `{baseline}/Story_Axis.md`

Read: `{baseline}/Act_Framework.md`

Read: `{baseline}/Core_Skeleton_{act_num}.md`

Read: `{baseline}/Worldbuilding.md`

Read: `{chars}/Character_Profiles.json`

Read: `{chars}/Relationship_Matrix.json`

Design and generate a writing guide that will instruct the AI to produce the novel prose.

## Design Principles

1. The guide must not repeat the plot. The plot is provided by the plot file. The guide only gives execution-level instructions.
2. Every instruction must be executable. After reading it, the AI should know exactly what to write and what not to write, rather than receiving vague direction.
3. Use fingerprints for style, not labels. Do not say "classical and elegant"; give concrete scales for sentence length, vocabulary, and rhetorical density.
4. Use texture for emotion, not category. Do not say "heavy and oppressive"; write "controlled heat," "slow cold," or "an anxiety lodged in the bones."
5. Taboos must be targeted, not generic. They should address the typical AI degradation modes of this particular story, not general writing advice.

## Output Requirements

- Prioritize quality, not length.
- Instructions must be concrete enough to write from directly.
- Prohibitions must be customized based on this story's genre, characters, and style.
- Strictly use the chapter structure below.

Write to: `{guides}/Writing_Guide_v{round}.md`

## 1. Narrative Coordinates

### 1.1 Position Anchor

- Identify the current act and scene, citing scene numbers from the plot file.
- State the settled event from the previous scene in one sentence and the entry point of the next scene in one sentence.
- Define this section's function in the overall arc: buildup, turn, release, or fall.

### 1.2 Scene Anchor

- Specific location, precise down to room, street, or time of day.
- Three to five objects that can serve as descriptive supports, labeled by function: information carrier, emotion carrier, or atmosphere carrier.
- Sensory anchors covering at least two channels: sight, hearing, smell, touch, taste.

### 1.3 Time Anchor

- In-story time, precise to time of day or number of days after an event.
- Time span inside the chapter: minutes, hours, or days.

---

## 2. Style Fingerprint

### 2.1 Sentence Features

- Main sentence-length range: mostly short sentences, alternating long and short, or mostly long sentences.
- Sentence preferences: archaic syntax, Europeanized syntax, colloquial breaks, inversion, or other patterns.
- Paragraph density: one sentence per paragraph, layered paragraph, or no line breaks inside a scene.

### 2.2 Lexical Field

- Era register: archaic vernacular, early modern vernacular, modern speech, or mixed.
- Professional or regional language traits: jargon, dialect words, technical terms, if any.
- Forbidden vocabulary direction, such as avoiding modern internet slang or avoiding excessive archaic ornamentation.

### 2.3 Rhetorical Density

- Number of rhetorical events per thousand words, such as metaphor, synesthesia, personification.
- Preferred rhetorical type: imagistic, contrastive, sensory, philosophical.
- Any special rhetoric: repetition, silence, fragmentation, stream-of-consciousness fragments.

### 2.4 Emotional Texture

- The texture of the dominant emotion, not its label. Examples: controlled heat, slow cold, anxiety lodged in the bones.
- Dominant emotion plus one or two variation points, specifying which event causes the emotional turn.

---

## 3. Character Voice

### 3.1 Main Characters

- Speech style: sentence endings, word preferences, tempo, whether the character often stops before saying the real thing.
- Behavioral traits: signature small actions, attitude toward specific objects, body-language patterns.
- Psychological state in this section. Write something like "He weighs two choices repeatedly, but when he speaks, he chooses a third," not "He is conflicted."

### 3.2 Relationship Dynamics

- The current substance of the relationship: whether the surface and inner layer match.
- Whether the relationship advances, freezes, or retreats in this section.
- The triggering event of the relationship change and the state after the trigger.

### 3.3 Supporting Character Scale

- Supporting character function: information delivery, atmosphere, contrast, foreshadowing, utility.
- Depth of depiction: named with a few lines, pure background, or passed over briefly.
- Whether this section needs to establish distinct recognizability for the supporting character.

---

## 4. Plot Execution

### 4.1 Required Events

- Cite specific node numbers or scene names from the plot file without restating the plot content.
- Execution priority for each node:
  - Must land: core event, cannot be omitted.
  - Flexible: order may be adjusted or events may be merged.
  - Cuttable: may be removed depending on length.

### 4.2 Information Density Control

- Which information must be revealed for the first time in this section and clearly received by the reader.
- Which information must be delayed, so the reader may guess but the text must not state it.
- Which information must be blurred, leaving doubt and room for reader imagination.

### 4.3 Emotional Arc

- Starting state: the character's emotion on entry.
- Turn trigger: which event, line, or detail causes the emotional shift.
- Ending state: the character's emotion on exit.
- Delayed release point: where the emotion is intentionally held back for a later section.

### 4.4 Foreshadowing and Payoff

- Cite foreshadowing IDs already marked in the plot file and identify which are paid off here.
- New foreshadowing planted in this section, specifying the concrete carrier: object, dialogue, or detailed action. Do not write outline-level statements; write the carrier.
- Degree of disguise: visible at first glance, noticeable on reflection, or fully hidden.

### 4.5 Ending Method

- Type of suspense at the end: unfinished sentence, unrevealed truth, absent arrival, emotional rumination, abrupt scene stop.
- Emotional direction of the last sentence: rising, sinking, flat, or reversed.
- Sentence feature of the last sentence: short, rhetorical question, unfinished, or image closure.

---

## 5. Rhythm Control

### 5.1 Length and Structure

- Word-count range, with upper and lower limits.
- Number of internal beats and approximate word-count ratio for each beat.

### 5.2 Paragraph Types and Rhythm Allocation

- Position and proportion of action paragraphs, psychological paragraphs, dialogue paragraphs, and silence paragraphs.
- Specific placements for slow motion, fast-forward, and silence.
- Tension-release ratio, such as three tight beats plus one loose beat, overall taut, or overall relaxed.

---

## 6. Targeted Taboos

### 6.1 Taboo List

- Customize each item for this story. One sentence per item, specific enough to recognize.
- Do not use generic examples or repeat default AI writing common sense.
- Form: "Do not..." + reason why this matters especially for this story.

### 6.2 High-Risk Positions

- Where this section is most likely to fail: rhythm, emotion, information, or style.
- Give one warning sentence for each risk point.

---

## 7. Expression Control

### 7.1 Presentation Priority

Emotion-expression order:

Action
> Detail
> Dialogue
> Psychology
> Conclusion

Prioritize showing phenomena. Do not directly explain emotion.

### 7.2 Character Realness

Allowed:

- Hesitation
- Misjudgment
- Half-spoken lines
- Answers that do not answer the question
- Sudden changes of mind

Forbidden: omniscient, all-competent thinking.

### 7.3 Detail Rules

Every core scene must contain at least:

- One character detail
- One environmental detail
- One object detail

Details must participate in the narrative.

Purely decorative description is forbidden.

### 7.4 Avoiding AI Degradation

Forbidden:

- Direct emotion definition
- Plot-report narration
- Sudden character-position reversal
- Sacrificing logic for payoff
- Lowering character intelligence to advance the plot

Every change must have a visible trigger chain.

Output path: `{guides}/Writing_Guide_v{round}.md`

Chapter position: Act {act_num}, Chapter {round}

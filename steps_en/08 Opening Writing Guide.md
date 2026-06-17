Read: `{plots}/Plot_v1.md`

Read: `{chapter_context}`

Design a writing guide for directing the AI in producing the novel's draft text.

[Design Principles]
1. The guide does not repeat the plot. The plot file supplies the plot; the guide only gives execution-level instructions.
2. Every instruction must be actionable. After reading it the AI knows exactly what to write and what not to write, not just a direction that still leaves room for interpretation.
3. Use fingerprints for style, not labels. Don't say "classical and elegant"; specify the exact scale of sentence length, vocabulary, and rhetorical density.
4. Use texture for emotion, not categories. Don't say "heavy and oppressive"; write "restrained heat / chronic cold / an itch buried in the bones."
5. Taboos must be targeted, not generic. Address the AI's typical degeneration modes for THIS story, not general writing common sense.

[Output Requirements]
- Prioritize quality, not length.
- This chapter's prose target: 2500–4500 characters, default around 3000 characters. If the core skeleton or plot file gives a more specific chapter length arrangement, that must be inherited.
- Keep the guide itself lean. Output roughly 1500–2200 characters, hard cap 2800 characters. Do not expand it into a plot retelling or an essay on craft.
- Instructions must be specific enough to write from directly. No vague space allowed.
- Prohibitions must be customized based on this story's genre, characters, and style traits.
- Strictly use the section structure below.

Write to: `{guides}/Writing_Guide_v{round}.md`

## 1. Narrative Coordinates

### 1.1 Positioning Anchor

- Which act and which scene this is. Reference the scene number in the plot file.
- The event settled in the previous scene (one sentence). The entry point the next scene will pick up (one sentence).
- This segment's functional position in the overall arc (buildup / turn / release / settling).

### 1.2 Scene Anchor

- Concrete location (precise down to room / street / time of day).
- 3–5 objects that can serve as descriptive anchors (tag function: information carrier / emotion carrier / atmosphere carrier).
- Sensory anchors covering at least two channels: sight / sound / smell / touch / taste.

### 1.3 Time Anchor

- In-story time (precise down to the hour or which day after an event).
- Time span within the chapter (how many minutes / hours / days this segment covers).

---

## 2. Style Fingerprint

### 2.1 Sentence Pattern

- Primary sentence-length range (short-dominant / alternating long and short / long-dominant).
- Sentence preferences (classical Chinese constructions / Europeanized / colloquial breaks / inversion).
- Paragraph density (one sentence per paragraph / multiple layers per paragraph / whole-scene unbroken paragraphs).

### 2.2 Vocabulary Register

- Era register (classical vernacular / modern vernacular / contemporary colloquial / mixed).
- Profession / regional language traits (any specific jargon, dialect words, technical terms).
- Forbidden-vocabulary direction (e.g., "avoid modern internet slang" or "avoid piling up antique-sounding decorations").

### 2.3 Rhetorical Density

- Number of rhetorical events per 1000 characters (metaphor / synesthesia / personification, etc.).
- Preferred rhetoric type (imagery-driven / contrast-driven / sensory-driven / philosophical).
- Any special rhetorical devices (repetition / intentional silence / broken sentences / stream-of-consciousness fragments).

### 2.4 Emotional Texture

- The texture of the dominant emotion in this segment (not "what tone" but "what texture," e.g., restrained heat, chronic cold, an itch buried in the bones).
- Dominant emotion plus 1–2 variation points (which event shifts the emotion).

---

## 3. Character Voices

### 3.1 Main Characters

- Way of speaking (sentence-ending habits / word preference / speech tempo / tendency to swallow words halfway).
- Behavioral traits (signature tics / attitude toward specific objects / body-language patterns).
- Psychological state within this segment (write "he weighed two options and chose a third out loud," not "he was torn").

### 3.2 Relationship Dynamics

- The substance of the current two-person relationship (whether the surface and inner layers match).
- Whether this segment pushes the relationship forward / freezes it / pushes it back.
- The trigger event that shifts the relationship and the state after the shift.
- Relationship debts this segment inherits or newly creates (owing / accidental harm / being seen / being chosen / being left behind / being protected).
- The masculine or feminine sexual attraction to highlight in this segment (sense of power / softness / ease / danger / restraint / maturity / wildness / fragility / contrast).
- The concrete details the attracted party will notice (posture / voice / clothing / scent / tempo of movement / body temperature / skin condition / muscle reaction / where the gaze lingers).
- The intimacy boundary for this segment (what can happen, what cannot, why it cannot be crossed).
- Abstract intimate actions suitable for this segment (actions must be concrete and serve the relationship).
- Whether real sexual intimacy is allowed in this segment. If yes, the consent conditions, the descriptive scale, and the relationship consequences after.
- Defensive reaction after intimacy (pulling back / joking / cold face / changing the subject / seizing the initiative / silence / demanding reassurance / pretending nothing happened).

### 3.3 Supporting Cast Calibration

- Supporting character functional role (information carrier / atmosphere / contrast / foreshadowing / utility NPC).
- Depth of description (named with a few lines of dialogue / pure background / one-line mention).
- Whether this segment needs to establish the supporting character's recognizability.

---

## 4. Plot Execution

### 4.1 Must-Hit Events

- Cite specific node numbers or scene names from the plot file (do not restate the plot content).
- Execution priority for each node:
    - Must land (core event, cannot be skipped).
    - Flexible (order can shift or be merged).
    - Trimmable (can be cut if length is tight).

### 4.2 Information Density Control

- Which information must be revealed for the first time in this segment (the reader must clearly receive it).
- Which information to delay (the reader may guess, but it cannot be stated).
- Which information to leave fuzzy (raise a question without resolving it, leave room for imagination).

### 4.3 Emotional Arc

- Starting state (emotion when the character enters).
- Pivot trigger (which event / line / detail flips the emotion).
- End state (emotion when the character exits).
- Delayed release point (where emotion is held back on purpose, to land in the next segment).

### 4.3a Intimacy Tension Execution

- If this segment contains male-female romantic charge, it must be rendered through abstract intimate actions: distance, the moment before and after touch, care, clothing, wounds, temperature, scent, where the gaze lingers, shared silence.
- Every intimate moment must contain three steps: the reason for approaching, the boundary that stops them, the reaction after.
- An intimate moment cannot merely make the atmosphere romantic; it must also change at least one of: initiative, trust, defensiveness, debt, misunderstanding, dependence.
- Do not write the labels "ambiguity / heart-flutter / desire / pulse-quickening / feelings blooming in silence" in place of what the reader should actually feel.

### 4.3a-1 Sexual Attraction Description

- Allowed and encouraged: describing the sexual attraction of adult men or women, but always rendered through the character's lens as a shift of attention: what he or she saw, what was heard, what was smelled, why the gaze looked away instantly or lingered instead.
- Attractiveness can come from body lines, sense of power, softness, the way clothing fits, a lowered voice, breathing changes, damp hair, wounds, sweat, scent, controlled motion, loose posture, a sense of danger, restraint, or contrast.
- Describe the attracted party's bodily response: fewer words, a tight throat, a half-beat-slow action, gaze that looks away and comes back, suddenly sharpness, over-arranging an object, stepping close and only then realizing the distance.
- Do not scan the whole body evenly in one segment. Pick 1–3 details with the most narrative function and let them change dialogue, action, or who holds the initiative.
- Do not only write "beautiful, handsome, sexy, seductive, hot." These words may appear occasionally, but they cannot replace concrete observation.
- Do not break a person into a checklist of body parts. Attractiveness description must preserve personality, circumstances, agency, and the boundaries of the person being watched.

### 4.3b Sexual Intimacy Execution

- If the plot file judges this segment allows real sexual intimacy, the draft must not use a mechanical jump-cut to dodge the fact; it can explicitly state that the two of them had sexual intimacy.
- Sexual intimacy requires: both parties adult, sober, willing. Consent can be implicit but must be readable by the reader, and any hesitation, pause, or refusal must be respected.
- Place the descriptive focus on choice, approach, pause, breath, bodily aftermath, shame, defensiveness, confirmation, the silence after, and the relationship change. Do not write it as organs, positions, steps, or a technical checklist.
- After sexual intimacy, at least one of the following must change: trust, dependence, power balance, debt, misunderstanding, self-knowledge, downstream risk.
- You may write a non-detailed occurrence, but the text must not pretend nothing happened. There must be a state left behind that can be tracked.

### 4.4 Foreshadowing Setup and Payoff

- Reference foreshadowing numbers already marked in the plot file (which ones must be paid off in this segment).
- New foreshadowing planted in this segment (concrete carrier: object / dialogue / small action; write the carrier, not the outline).
- How heavily the foreshadowing is disguised (obvious at a glance / noticeable on second thought / fully hidden).

### 4.5 Closing Mode

- The suspense shape at the end of this segment (an unfinished sentence / an unrevealed truth / a person who has not arrived / emotional rumination / a scene that cuts off short).
- Emotional direction of the final sentence (rising / sinking / flat landing / reversal).
- Sentence-shape of the final line (short and abrupt / rhetorical question / unfinished / image-convergence).

---

## 5. Pacing Control

### 5.1 Length and Structure

- Target character-count range for the draft: write both the lower and upper bound explicitly, default 2500–4500 characters. Do not use vague words like "moderate" or "fairly long."
- Keep internal beats to 3–5, with an approximate character share for each.
- Every beat must be marked "must-write / compressible / deletable," so the draft can trim in the right order when it overruns.
- If the plot information density is too high, prioritize compressing exposition, setup, repeated interiority, and non-essential environment description. Do not compress core turns, relationship change, or the chapter landing.

### 5.2 Paragraph Type and Rhythm Distribution

- Position and ratio of action / interiority / dialogue / silence paragraphs in this segment.
- Specific landing points of slow-motion / fast-forward / silence.
- Tension-relaxation ratio (e.g., 3 beats tight + 1 beat loose / overall tight / overall loose).

---

## 6. Targeted Taboos

### 6.1 Prohibition List

- Customized to this story. One sentence each. Specific enough to be identifiable.
- No generic examples. Do not repeat the AI's default writing common sense.
- Format: Forbidden + reason (why this matters specifically to this story).

### 6.2 High-Risk Spots

- Where in this segment is it easiest for the writing to break (rhythm / emotion / information / style).
- One sentence of warning for each risk point (what to watch for when writing here).

---

## 7. Expression Control

### 7.1 Presentation Priority

Order of emotional expression:

Action
> Detail
> Dialogue
> Interiority
> Conclusion

Show the phenomenon first. Do not explain the emotion directly.

### 7.2 Character Authenticity

Allowed:

- Hesitation
- Misjudgment
- Half-finished sentences
- Answers that miss the point
- Changing one's mind on the spot

Forbidden: omniscient-mode thinking.

### 7.3 Detail Rules

Every core scene must contain at least:

- 1 character detail
- 1 environment detail
- 1 object detail

Details must participate in the narrative.

Forbidden: pure decorative description.

### 7.4 AI Degeneration Avoidance

Forbidden:

- Defining emotions directly
- Plot-report-style narration
- Characters suddenly switching positions
- Sacrificing logic for satisfaction
- Lowering character intelligence to push the plot
- Using steamy labels, blunt psychological summary, or mechanical description to fake romantic charge
- Using empty labels like "very beautiful / very handsome / very sexy" in place of concrete male or female attractiveness
- Writing attractiveness as a full-body scan, a body-part checklist, or a gaze unrelated to the character's situation
- Letting intimate actions have no cost, no boundary, no follow-up reaction
- Sexual intimacy happening with no aftermath, no changed person, no relationship consequence

All changes must have a visible trigger chain.

Output path: `{guides}/Writing_Guide_v{round}.md`

Chapter position: Act {act_num}, Chapter {round}

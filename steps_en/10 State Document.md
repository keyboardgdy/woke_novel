# State Document v{round}

## Files to Read

- `{output}/Draft_v{round}.md`
- `{plots}/Plot_v{round}.md`
- `{chapter_context}`

---

## Role

You are not a plot summarizer.

You are the "story state engine." Your only job is to extract from this round's plot:

- States that actually changed
- Emotions that will keep affecting the story next round
- Unfinished relationships and desires
- Lingering tension that makes the reader keep reading

Core task: generate a single, coherent piece of narrative-style distillation, serving as this round's "story synopsis fragment," at 120–180 characters (consistent with the step 15 loop segment; for the opening chapter a slightly shorter version is acceptable). This paragraph must:
1. Focus on the core dramatic turn of this round's plot.
2. Be written in a vivid, concise narrative voice.

Forbidden:

- Plot recap
- Literary-style summary
- Authorial interpretation
- Filling in unstated material
- Speculating about future plot

All information must come strictly from: `{output}/Draft_v{round}.md` and `{plots}/Plot_v{round}.md`.

---

## Part One: Draft Ending Quote

Extract the ending of the draft from `{output}/Draft_v{round}.md`. Not too much, just enough to bridge. 100–180 characters.

---

## Part Two: State Document

Write to: `{state}/State_v{round}.md`

---

```markdown
# Story State v{round}

# Story Synopsis

(Distillation of this round's plot content, 120–180 characters, no line breaks, no paragraph breaks, written until the natural narrative pause of this round.)

---

# Draft Ending Quote

> [Full quote of the last paragraph / ending of the draft]

---

# Scene Freeze

## Character Final State
- Position:
- Posture:
- Gaze:
- Hand action:
- Breath / physical state:

## Space Final State
- Lighting:
- Doors / windows:
- Important objects:
- Ambient sound:
- Air / temperature feel:

## Emotional Freeze Point
- Surface emotion:
- Deep suppression:
- Unexpressed emotion:

## Current Relationship Pressure
- Distance change:
- Initiative holder:
- Trust change:
- Defensiveness change:

## Last Unfinished Action
[one sentence]

## Last Unfinished Line
[one sentence]

## Lingering Desire from This Round
[one sentence]

## Unfulfilled Intimacy from This Round
- Reason to approach:
- Boundary that stopped them:
- Reaction after:
- Relationship afterecho:

## Sexual Attraction Memory from This Round
- Bodily appeal that was noticed:
- Observer's reaction:
- Whether the person being watched noticed:
- Impact on relationship initiative:

## Sexual Intimacy State from This Round
- Whether it occurred:
- Consent expression:
- Bodily aftermath:
- Psychological defense:
- Relationship consequence:
- Downstream risk:

---

# relationship_state

```yaml
relationship_state:
  pair:
    - [Role A]/[Role B]
  previous_state:
    - [Previous relationship stage]
  current_state:
    - [Current relationship stage]
  tension_delta: [numeric change]
  intimacy_delta: [numeric change]
  trust_delta: [numeric change]
  emotional_shift:
    - "[Emotion change added this round]"
  hidden_change:
    - "[Hidden relationship change]"
  unresolved_gap:
    - "[Currently unresolved relationship fracture]"
  intimacy_memory:
    - "[Intimate action, distance change, or care that happened this round but was not spoken aloud]"
  delayed_payoff:
    - "[Emotional return that should be paid out later]"
  sexual_intimacy_state:
    occurred: [true/false]
    consent_signal: "[If it happened, record how both sides expressed willingness; blank if it did not]"
    aftermath: "[Bodily aftermath, psychological defense, relationship consequence]"
    unresolved_risk: "[Downstream risk or unspoken question]"
```

---

# foreshadowing_state

```yaml
foreshadowing_updates:
  newly_planted:
    - id: FS_XXX
      type: [foreshadowing type]
      content: "[Newly planted foreshadowing content]"
  progressed:
    - id: FS_XXX
      progress: +1
  recovered:
    - id: FS_XXX
      payoff_type: [payoff type]
```

---

# rhythm_state

```yaml
rhythm_state:
  current_rhythm: [current rhythm]
  pacing: slow/medium/fast
  tension_trend: rising/falling/stable
  consecutive_high_tension_rounds: [number]
  next_required_rhythm: [recommended next-round rhythm]
  book_progress_pct: [0-100, calculated from total chapter count]
  planned_zone: "[from Act Framework rhythm design]"
  actual_vs_planned: "[on_track / ahead / behind / flatline]"
  macro_tension_history: "[compact encoding of recent chapter tension levels: e.g. LMMHHMMLHH]"
```

---

# theme_state

```yaml
theme_state:
  core_question: "[inherited from Story Axis]"
  current_position: "[protagonist's initial stance established in this chapter]"
  chapter_complication: "[how this chapter introduces / complicates the core question]"
  reader_lean: "[which side readers likely lean toward currently]"
```

---

# symbol_state

```yaml
symbol_state:
  active_symbols:
    - id: SYM_001
      carrier: "[object / imagery / sensory detail established in this chapter]"
      current_meaning: "[initial semantic value]"
      appearances: [1]
      trajectory: "[expected semantic direction]"
  chapter_usage:
    - id: SYM_001
      context: "[how this chapter introduced the imagery]"
```

---

# subplot_state

(For the opening chapter most subplots are not yet started; only record seeds already laid)

```yaml
subplot_state:
  active_subplots:
    - id: SP_001
      name: "[subplot name, if already named]"
      owner: "[main character]"
      arc_phase: setup
      last_beat_round: 1
      next_expected_beat: "[description]"
      main_plot_link: "[how it applies pressure to the mainline]"
  dormant_subplots: []
```

---

# reader_knowledge_state

```yaml
reader_knowledge_state:
  known_truths:
    - "[basic facts the chapter established for the reader]"
  active_mysteries:
    - id: RM_001
      question: "[the first mystery the chapter opened]"
      opened_round: 1
      planned_reveal: "[estimated reveal timing]"
  false_beliefs:
    - id: FB_001
      belief: "[false认知 the chapter deliberately let readers form, if any]"
      planted_round: 1
      correction_plan: "[when and how to overturn]"
  recent_reveals: []
```

---

# Core Character State

## [Protagonist Name]
- Core desire:
- Core fear:
- Current state:
- Current suppression:
- Current relationship demand:

## [Other Core Character]
- Core desire:
- Core fear:
- Current state:
- Current suppression:
- Current relationship demand:

---

# memory_digest

```yaml
long_term_memory:
  - "[events with long-term continuing impact]"
mid_term_memory:
  - "[mid-term impact events]"
discarded_memory:
  - "[information with no further value]"
```

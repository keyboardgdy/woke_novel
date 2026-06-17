Read: `{baseline}/Creative_Proposal_{option_index}.md`

Read: `{baseline}/Worldbuilding.md`

---

## Core Task

Based on the creative proposal and worldbuilding, generate core character profiles and a relationship matrix, output as structured JSON.

**Design Principle**: Characters are not data tables — they are "a collection of contradictions." The mark of a good character is this: the thing they want most and the thing they fear most point in the same direction.

---

## Design Guidance

### What Makes a Character Worth Writing

- There is tension between desire and fear: what they pursue requires confronting exactly what they avoid
- Self-awareness has blind spots: what they think they are differs from what their actual behavior reveals
- They have an independent ledger of interests: they are not tools serving the protagonist, they have something of their own to fight for
- Their action logic is self-consistent: given their past and personality, the reader will afterward feel "they really had no choice but to act this way"

### Character Hierarchy

- **Core characters** (3–5): fill in all fields completely, each field carefully designed
- **Important supporting characters** (2–4): fill in basic fields plus relationship fields related to the main plot; some intimate detail fields may be omitted
- **Do not** generate marginal characters with no subsequent function just to fill a count

### Field Standards

- Ordinary fields: 1–2 sentences; complex fields: maximum 3 sentences
- Array fields: keep only the 2–5 most reusable items
- All descriptions must be concrete — "afraid of being abandoned" is not as good as "afraid that when they finally speak up and ask for help, the other person has already turned and walked away"

---

## Boundary Constraints

Character profiles only describe "what kind of person the character is" and "how relationships will naturally heat up, retreat, and accumulate debt":

- ❌ Do not design chapter-level specific actions or decisions
- ❌ Do not design complete conflict event chains
- ❌ Do not design completed growth arcs
- ❌ Do not design finished scenes for specific chapters
- ✅ Describe the character's essential contradictions, behavioral tendencies, relationship starting point, and possible directions of change

---

## Character Profile JSON Structure

Each core character contains the following fields:

```json
{
  "name": "",
  "role": "",
  "surface_traits": [],
  "background": "",
  "ability_or_resource": "",
  "core_desire": "",
  "core_fear": "",
  "emotional_wound": "",
  "unspoken_need": "",
  "shame_point": "",
  "moral_boundary": "",
  "relationship_habit": "",
  "intimacy_trigger": "",
  "intimacy_defense": "",
  "sensual_appeal": "",
  "physical_presence": "",
  "attractive_details": [],
  "self_awareness_of_appeal": "",
  "sexual_boundary": "",
  "consent_language": "",
  "after_intimacy_response": "",
  "body_language_when_moved": "",
  "body_language_when_defensive": ""
}
```

**Key field explanations** (only explaining commonly misunderstood ones):

| Field | What to write | What NOT to write |
| --- | --- | --- |
| emotional_wound | The old wound most easily poked | Piling up tragic backstory |
| unspoken_need | What they most want from others but are too ashamed to admit | Generic "being loved" |
| shame_point | The vulnerability that, once seen, triggers defense/attack/flight | Ordinary weaknesses |
| intimacy_trigger | Concrete situations that shake the character | Generic descriptions like "being treated gently" |
| sensual_appeal | The texture of the appeal source (strength / ease / danger / restraint / contrast…) | "Very handsome/beautiful" |
| physical_presence | The body's presence when entering a space (posture / gait / voice / scent / temperature / the way clothing sits / movement rhythm) | Static appearance checklist |
| attractive_details | 2–5 sensory-perceptible details others repeatedly notice | "Exquisite features," "good figure" |
| consent_language | How they express willingness / hesitation / refusal in a way that fits their character | Generic templates |

---

## Relationship Matrix JSON Structure

Each important relationship pair contains the following fields:

```json
{
  "pair": ["Character A", "Character B"],
  "surface_relation": "",
  "inner_relation": "",
  "attraction_source": "",
  "sexual_attraction_source": "",
  "gaze_pattern": "",
  "desire_tells": [],
  "repulsion_source": "",
  "power_balance": "",
  "relationship_debt": "",
  "unspoken_rule": "",
  "intimacy_boundary": "",
  "sexual_threshold": "",
  "consent_risk": "",
  "boundary_crossing_risk": "",
  "slow_burn_path": [],
  "abstract_intimacy_motifs": [],
  "possible_sexual_payoff": "",
  "delayed_payoff": ""
}
```

**Key field explanations**:

| Field | What to write | What NOT to write |
| --- | --- | --- |
| inner_relation | The true pull, misunderstanding, dependence, wariness, or desire | Repeating surface_relation |
| sexual_attraction_source | Concrete source of attraction (physical contrast / scent memory / voice / being needed…) | "They like each other" |
| gaze_pattern | Where the gaze lingers when drawn in, how it moves away, how it conceals itself | Organ-checklist staring |
| desire_tells | Small actions that leak desire (fewer words / slowed movement / suddenly sharp…) | Directly saying "they're attracted" |
| relationship_debt | Unpaid emotional debt | Generic "deep feelings" |
| slow_burn_path | Stages of warming (only stage names and costs) | Specific chapter-by-chapter plot |
| abstract_intimacy_motifs | Intimate actions/objects/distances suitable for recurring use | Direct sexual description |
| consent_risk | The point where consent expression is most likely to become ambiguous | Ignoring this field |

---

## Bottom-Line Principles

All intimacy, sensual attraction, and sexual intimacy design must be built on the premise of: adult characters, sober and willing consent, and logically established relationship.

The design focus must be on character perspective, desire, consent, shame, choice, and relationship consequence — not reducing characters to organ checklists or possession objects. It is allowed to depict the sensual attraction of male and female characters, and to let sexual intimacy actually occur in the story, but characters' boundaries, dignity, and action logic must not be compromised for this.

---

## Output

1. Write the character profiles to `{chars}/Character_Profiles.json`
2. Write the relationship matrix to `{chars}/Relationship_Matrix.json`

Output path: `{chars}/Character_Profiles.json`
Output path: `{chars}/Relationship_Matrix.json`

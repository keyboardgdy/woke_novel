Read: `{plots}/Plot_Direction_v{round}.md`

Read: `{plots}/Plot_v{round}.md`

Read: `{quality}/Plot_Appeal_Review_v{round}.md`

Read: `{chapter_context}`

You are the plot-rewrite editor of a serialized novel. Your task is to strengthen the appeal of this chapter's plot outline, not to draft prose.

## Rewrite Principles

1. Do not change the story axis or this act's core skeleton.
2. Do not manufacture stimulation with coincidence. Events must be triggered by character choice, misjudgment, concealment, probing, attack, or evasion.
3. Prioritize fixing P01, P02, P03, P05, P09.
4. Every rewrite must add at least one of: a clearer desire, a more painful cost, a stronger information gap, more concrete resistance, or a sharper chapter-end debt.
5. If the review tags P13, P14, P15, you must add relationship debt, intimacy boundary, and post-intimacy aftertaste — not only external events.
6. If the review tags P16, P17, you must judge whether sexual intimacy should really happen this chapter. If it does, supply the consent condition, the reason it happens, and the relationship consequence. If it does not, supply the explicit boundary that prevents it.
7. If the review tags P18, P19, supply the trigger for either male or female sensual attraction, and make it change the dialogue, distance, action, initiative, or misreading.
8. Preserve the effective foreshadowing, character-relationship movement, and must-hit events from the original outline.
9. If the review tags P20, P21, you must adjust this chapter's rhythm position or switch the conflict type so it matches the plot direction and does not repeat the previous chapters.
10. If the review tags P22, you must have this chapter touch the core question from a new angle, causing the protagonist's stance to perceptibly change.
11. If the review tags P23, you must add subplot beats (advance at least one active subplot) or clearly state the reasonable suspension reason.
12. If the review tags P24, you must adjust the information release rhythm — add a new mystery, delay a reveal, or reinforce a false belief.

## What This Chapter Must Have

```yaml
chapter_attraction:
  promise: "The clear return this chapter gives the reader"
  pressure: "The pressure that drives the character to act"
  turn: "The irreversible shift in the middle"
  payoff: "The pleasure / pain / suspense point delivered this chapter"
  debt: "The unpaid debt left at the chapter end"
  relationship_debt: "The relationship debt this chapter advances or deepens"
  sensual_appeal: "The male / female sensual attraction triggered this chapter, and how it changes the relationship action"
  intimacy_boundary: "The intimacy boundary this chapter approaches but does not casually cross"
  sexual_intimacy: "Whether sexual intimacy happens this chapter; if so, record the consent condition and relationship consequence; if not, record the boundary that blocks it"
  aftertaste: "The emotional aftertaste left by the intimacy, misreading, or retreat"
  foreshadowing_carrier: "Foreshadowing this chapter advances or newly plants (object / dialogue / detail action), cite foreshadowing_state ID if any"
  theme_touch: "How this chapter touches the core question, what changes in the protagonist's stance"
  subplot_beat: "Subplot this chapter advances and its beat"
  info_asymmetry: "The information gap manipulation this chapter (what the reader should newly know / continue to misbelieve / newly wonder about)"
```

The above structure is for your internal design. Do not output it separately.

## Output Path

Overwrite: `{plots}/Plot_v{round}.md`

Also write: `{quality}/Plot_Appeal_Rewrite_Note_v{round}.md`

## Plot Outline Output Requirements

- Output only one continuous plot outline.
- Keep the plot outline within 700–1100 characters, hard cap 1400 characters (the strengthened version must carry more appeal density than the original, so the character budget is slightly wider than step 12).
- Be specific, clear, and visually evocative.
- Do not write prose dialogue, do not write literary description.
- Do not use the em dash `——`.
- Must be able to drive the next step's writing guide.
- If content is too much, prioritize compressing background explanation, emotional commentary, environmental setup, and repeated interiority. Keep the core events, causal turns, relationship changes, and chapter-end debt.

## Rewrite Notes Format

Keep the rewrite notes within 600–1100 characters, hard cap 1400 characters. Write only the actual changes and the downstream risk. Do not recap the full plot and do not repeat the review text.

```markdown
# Plot Appeal Rewrite Note v{round}

## Problems Fixed

- [Defect code] [Corresponding plot-layer fix action]

## New Appeal Added

- Desire:
- Cost:
- Resistance:
- Reversal / discovery:
- Chapter-end debt:
- Relationship debt:
- Sensual attraction:
- Intimacy tension:
- Sexual intimacy handling:

## Preserved Content

- [Effective content kept from the original plot]

## Risk Warning

- [Risks the downstream writing guide and chapter body must watch]
```

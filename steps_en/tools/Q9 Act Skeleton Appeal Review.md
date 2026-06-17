Read: {baseline}/故事主轴.md
Read: {baseline}/幕次框架.md
Read: {baseline}/核心骨架_{act_num}.md
{prev_act_skeleton}
Read: {baseline}/创意方案_{option_index}.md
Read: {baseline}/世界观.md
Read: {chars}/人物档案.json
Read: {chars}/关系矩阵.json
Read: {quality}/幕次框架吸引力评审.md (if it exists)

You are an act-level plot editor. Your task is to judge whether `核心骨架_{act_num}.md` for Act {act_num} can sustain a whole act of continuous continued reading.

Do not critique single-chapter prose. Judge only whether this act's beat chain has strong hooks, escalating resistance, a mid-act reversal, crisis, climax payoff, and act-end debt, and whether each beat can be split into chapters naturally.

The review must be short and actionable:
- Keep the total at 1000-1800 characters, with a hard cap of 2200 characters.
- List only the 3-5 most important beat problems. Do not write long per-beat comments.
- Each problem must include skeleton evidence and a beat-layer fix.

## Scoring Dimensions

Total: 100.

- Act core question 15: does the act have a clear and strong core conflict question.
- Hook strength 10: does the act's opening quickly build reader anticipation.
- Beat escalation 20: do Hook / Setup / Midpoint / Crisis / Climax / Resolution escalate beat by beat.
- Beat causality 15: is each beat forced out by the consequences of the previous beat.
- Midpoint turn 10: does the Midpoint change the goal, cognition, initiative, or risk level.
- Crisis cost 10: does the Crisis force the character to lose, sacrifice, or expose a weakness.
- Climax payoff 10: does the Climax pay off the act's promise rather than only postponing it.
- Act-end debt 5: does the Resolution leave a reason to keep reading into the next act.
- Chapter mapping 5: do the chapter counts covered by the beats stay reasonable, without squeezing the major turns.

## Defect Codes

- C01 Act-level core question is weak
- C02 Hook is not grabbing
- C03 Beat escalation is flat
- C04 Beat causality is broken
- C05 Midpoint has no turn
- C06 Crisis has no cost
- C07 Climax does not pay off
- C08 Act-end debt is insufficient
- C09 Chapter mapping is unbalanced
- C10 Side lines drift from the main line
- C11 Repeats the previous act
- C12 Beats cannot be split into chapters

## Output Path

Write to: {quality}/核心骨架吸引力评审_{act_num}.md

If the content gets too long, prioritize compressing the per-dimension judgments and explanations. Keep this act's continued-reading promise, beat problems, and must-adjust list.

## Output Format

```markdown
# 核心骨架吸引力评审 第{act_num}幕

## 总分

[0-100]

## 门禁结论

[通过 / 调整节点 / 重构本幕骨架 / 回退幕次框架]

## 本幕追读承诺

[One sentence explaining why a reader should read the whole act; if you cannot, write: 无]

## 分项评分

| 维度 | 分数 | 判断 |
| --- | ---: | --- |
| 幕级核心问题 |  |  |
| Hook 强度 |  |  |
| 节点递进 |  |  |
| 节点因果 |  |  |
| 中点翻转 |  |  |
| 危机代价 |  |  |
| 高潮兑现 |  |  |
| 幕末欠账 |  |  |
| 章节映射 |  |  |

## 节点问题

1. [缺陷码] [One-sentence problem]
   - 证据：[Quote or precisely paraphrase the problem in the core skeleton]
   - 影响：[Why it weakens this act's continued-reading pull]
   - 改法：[Beat-layer fix]

## 必须调整

- [3-7 beat-level adjustment actions, in priority order]

## 禁止破坏

- [Beats, reversals, crises, climaxes, or act-end hooks that are already effective]
```

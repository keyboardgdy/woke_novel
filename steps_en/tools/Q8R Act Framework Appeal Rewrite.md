Read: {baseline}/故事主轴.md
Read: {quality}/故事主轴吸引力评审.md (if it exists)
Read: {quality}/故事主轴重构说明.md (if it exists)
Read: {baseline}/幕次框架.md
Read: {quality}/幕次框架吸引力评审.md
Read: {baseline}/创意方案_{option_index}.md
Read: {baseline}/世界观.md
Read: {chars}/人物档案.json
Read: {chars}/关系矩阵.json

You are a long-form serial structure editor. Your task is not to rewrite the story axis, but to apply gate-level strengthening to `幕次框架.md` based on `幕次框架吸引力评审.md`.

## Rewrite Principles

1. Prioritize fixing the B01-B10 problems flagged in the review.
2. Do not change the story axis's core question, final cost, or key turns.
3. Preserve the act functions, climax positions, foreshadowing distribution, and character arcs that the review marks as not to break.
4. If the review conclusion is "pass", make only light calibration and do not change the total act count.
5. If the review conclusion is "adjust acts" or "rebuild act framework", make the continued-reading curve, hook distribution, payoff rhythm, and chapter budget clearer.
6. Do not expand into single-chapter plot, do not write prose scenes.

## Output Path

Overwrite: {baseline}/幕次框架.md

Also write: {quality}/幕次框架重构说明.md

## Act Framework Output Requirements

- Keep the whole act framework within 2500-4000 characters, hard cap 5000 characters (aligned with step 05a Act Framework).
- Each act should write only structural function, core conflict, chapter budget, character / relationship change, and act-end hook.
- Must preserve this exact marker for automated extraction:

```markdown
幕次总数：N幕
```

## Rewrite Notes Format

Keep the rewrite notes within 600-1100 characters, hard cap 1400 characters. Write only the actual changes and residual risks. Do not recap the full framework.

```markdown
# 幕次框架重构说明

## 门禁处理

- 原评审结论：
- 本次处理结果：[通过 / 已调整 / 仍需人工确认]

## 已修复问题

- [缺陷码] [Corresponding act-layer fix action]

## 强化后的追读曲线

- 幕次功能差异：
- 加压路径：
- 钩子分布：
- 爽点/痛点兑现：
- 篇幅预算：
- 幕末欠账：

## 保留内容

- [Effective original framework material preserved]

## 残留风险

- [Risks the downstream act skeleton must handle]
```

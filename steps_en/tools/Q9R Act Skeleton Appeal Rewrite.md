Read: {baseline}/故事主轴.md
Read: {baseline}/幕次框架.md
Read: {quality}/幕次框架吸引力评审.md (if it exists)
Read: {quality}/幕次框架重构说明.md (if it exists)
Read: {baseline}/核心骨架_{act_num}.md
Read: {quality}/核心骨架吸引力评审_{act_num}.md
{prev_act_skeleton}
Read: {baseline}/创意方案_{option_index}.md
Read: {baseline}/世界观.md
Read: {chars}/人物档案.json
Read: {chars}/关系矩阵.json
Read: {evolution}

You are an act-level plot editor. Your task is not to rewrite the whole book, but to apply gate-level strengthening to Act {act_num}'s `核心骨架_{act_num}.md` based on `核心骨架吸引力评审_{act_num}.md`.

## Rewrite Principles

1. Prioritize fixing the C01-C12 problems flagged in the review.
2. Do not change the core promises of the story axis or the act framework.
3. Preserve the beats, reversals, crises, climaxes, or act-end hooks that the review marks as not to break.
4. If the review conclusion is "pass", make only light calibration and do not change this act's chapter count.
5. If the review conclusion is "adjust beats" or "rebuild act skeleton", strengthen the hook, beat escalation, midpoint turn, crisis cost, climax payoff, and act-end debt.
6. Each beat should still be written only at the act-skeleton level, not expanded into single-chapter outlines or prose scenes.

## Output Path

Overwrite: {baseline}/核心骨架_{act_num}.md

Also write: {quality}/核心骨架重构说明_{act_num}.md

## Core Skeleton Output Requirements

- Keep the whole core skeleton within 2500-4000 characters, hard cap 5000 characters (aligned with step 05b Act Core Skeleton).
- Prefer the mainline-beat table.
- Each beat must include: core turn, causal chain, character change, relationship debt / intimacy boundary, and chapter mapping.
- Must preserve this exact marker for automated extraction:

```markdown
章节数：N章
```

幕次定位：第{act_num}幕

## Rewrite Notes Format

Keep the rewrite notes within 600-1100 characters, hard cap 1400 characters. Write only the actual changes and residual risks. Do not recap the full skeleton.

```markdown
# 核心骨架重构说明 第{act_num}幕

## 门禁处理

- 原评审结论：
- 本次处理结果：[通过 / 已调整 / 仍需人工确认]

## 已修复问题

- [缺陷码] [Corresponding beat-layer fix action]

## 强化后的幕级追读

- 本幕核心问题：
- Hook：
- 节点递进：
- 中点翻转：
- 危机代价：
- 高潮兑现：
- 幕末欠账：
- 章节映射：

## 保留内容

- [Effective original skeleton material preserved]

## 残留风险

- [Risks the downstream chapter context pack and plot design must handle]
```

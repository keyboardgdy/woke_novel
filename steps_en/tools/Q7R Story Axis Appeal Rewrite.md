Read: {baseline}/创意方案_{option_index}.md
Read: {baseline}/故事主轴.md
Read: {quality}/故事主轴吸引力评审.md
Read: {baseline}/世界观.md
Read: {chars}/人物档案.json
Read: {chars}/关系矩阵.json
Read: {evolution}

You are the chief editor of a long-form serialized novel. Your task is not to invent a different book, but to apply gate-level strengthening to `故事主轴.md` based on `故事主轴吸引力评审.md`.

## Rewrite Principles

1. Prioritize fixing the A01-A10 problems flagged in the review.
2. Do not overturn the selected creative proposal, the core world rules, or the major character relationships.
3. Preserve the effective hooks, desires, rules, and emotional engine that the review marks as not to break.
4. If the review conclusion is "pass", make only light calibration and do not expand the worldbuilding.
5. If the review conclusion is "strengthen axis" or "rebuild axis", make the whole-book core question, long-line desire, final cost, opposition system, and escalation curve more concrete.
6. Do not write single-chapter plot, prose scenes, dialogue, or expanded side-story detail.

## Output Path

Overwrite: {baseline}/故事主轴.md

Also write: {quality}/故事主轴重构说明.md

## Story Axis Output Requirements

- Keep the whole story axis within 2500-4000 characters, hard cap 5000 characters (aligned with step 05 Story Axis).
- Mainline nodes limited to 5-8.
- Each node should write only the core turn, causality, function, and character change.
- Must include: one-line mainline, core question, drivers, mainline nodes, key turning points, emotional destination, and long-line emotional engine.
- Do not use the em-dash `——`.

## Rewrite Notes Format

Keep the rewrite notes within 600-1100 characters, hard cap 1400 characters. Write only the actual changes and residual risks. Do not recap the full axis.

```markdown
# 故事主轴重构说明

## 门禁处理

- 原评审结论：
- 本次处理结果：[通过 / 已补强 / 仍需人工确认]

## 已修复问题

- [缺陷码] [Corresponding axis-layer fix action]

## 强化后的追读引擎

- 核心问题：
- 长线欲望：
- 终局代价：
- 阻力系统：
- 升级曲线：
- 情绪引擎：

## 保留内容

- [Effective original axis material preserved]

## 残留风险

- [Risks the downstream act framework must handle]
```

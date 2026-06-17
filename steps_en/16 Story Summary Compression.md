## Files to Read

Read: `{state}/Story_Summary.md`

## Role

Act as a story structure expert and compress the current long `Story_Summary.md`.

Your work:

1. Strictly edit, merge, and polish based on the existing narrative text. Do not change its plain-text, paragraph-style narrative format.
2. Remove secondary details, repeated descriptions, and transitional sentences. Merge multiple sentences that describe the same event.
3. Preserve all key plot turns, major character decisions, emotional high points, and unresolved suspense.

After each compression, the Story Summary body should stay within 1000-1800 characters, hard cap 2200 characters. If the current summary is still short, do not pad it to hit the lower bound; only deduplicate and smooth the sentences.

## Core Requirements

Compression is not deletion; it is condensation.

Preserve:

- The core plot chain, including setup, development, turn, and consequence
- Key turning points
- The protagonist's core goal and conflict
- The story ending, if one exists

Delete:

- Details of transitional plot
- Repeated emotional setup
- Nonessential side-plot information

If the current summary is too long, preferentially merge events of the same kind, delete repeated emotion, and compress transitional action, but you must preserve key turns, major character decisions, emotional high points, and unresolved suspense. The output must be only the compressed story summary; do not explain the reasoning behind the edits.

## Output

Update the story summary in `{state}/Story_Summary.md`. The format must remain strictly:

Output path: `{state}/Story_Summary.md`

```markdown
# Story Summary

[compressed content]
```

Do not output `# Compressed Story Summary` or any other variant title.

# Benchmark Notes

These notes are intentionally modest. They are not a lab benchmark; they are practical validation data from normal development use.

## 2026-04-30 validation

Task family:

- structured extraction;
- filename/doc classification;
- citation/package-style notes;
- aphorism or concept mining with tags.

Observed result:

- MCP inline and OpenCode/relay style usage both produced usable output;
- no factual errors were observed in the small validation set;
- MCP was fastest and best for immediate one-off output;
- OpenCode/relay style work was better when per-item rationale or staged artifacts mattered.

## Practical rule

Use MCP inline when:

- the answer will be consumed immediately;
- the task is one prompt;
- you want a table, JSON, summary, or classification.

Use a staged workpack when:

- the output should become a file packet;
- each item needs rationale;
- another agent or human will review and promote selected pieces.

## Latency

Latency varies with prompt size, model, network, and provider load.

In local doc-ops style tasks, small structured prompts often landed in the tens-of-seconds range. Tiny smoke tests can return much faster. Avoid hardcoding latency claims into product decisions.

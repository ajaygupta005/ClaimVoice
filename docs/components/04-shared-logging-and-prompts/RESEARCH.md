# Component 04 - Shared Logging + Prompts Packages - Research

> Alternatives considered, decisions made, references.

## loguru vs stdlib logging
- loguru: zero-config, structured-by-default, sinks for JSON output, faster than stdlib for our throughput.
- stdlib is fine but requires ~50 lines of boilerplate per service to match.

## pino vs winston
- pino is the fastest JSON logger in Node; winston is slower and has a clunkier API.
- pino-pretty for local dev; pure JSON in production.

## One schema across two languages
- A single Loki/CloudWatch query language for all logs is worth a lot.
- Diverged schemas mean queries break when a service is rewritten in the other language.

## Why version prompts as code (not config)
- Review diffs on PR; CODEOWNERS can require sign-off from the prompts owner.
- Eval suite can be wired to test prompt changes before merge.

## References
- loguru: https://loguru.readthedocs.io/
- pino: https://github.com/pinojs/pino
- Anthropic prompt engineering: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview


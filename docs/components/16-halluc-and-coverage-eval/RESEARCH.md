# Component 16 - Hallucination + Coverage QA Evals - Research

## Why model-graded
Exact match is too brittle for free-form Q&A. Embedding similarity is
noisy. A judge LLM trained on QA grading (Inspect AI's `model_graded_qa`)
gives us a usable signal at this scale.

## Why a separate hallucination eval
Hallucination is a different failure mode from "wrong answer". An answer
can be factually wrong while still being grounded in given context (the
context itself was wrong). A separate task forces us to measure
groundedness directly.

## Judge model choice
We use whatever Inspect AI defaults to (Claude Sonnet). Production should
use a different family (Claude Opus or GPT-4o) to reduce shared blind
spots between agent and judge.


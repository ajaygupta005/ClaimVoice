# Component 35 - WS-7 Claude Answer Composer

> **Workstream**: WS-7 real LLM integration  
> **Depends on**: Component 34 - WS-7 Agent Evaluation Harness

## Goal

Add the first real Anthropic Claude call inside the voice-agent LangGraph runtime.

Claude should replace the mock answer composer node only.

Claude must not choose tools, invent plan facts, call databases directly, or bypass the hallucination guard.

The graph should still own:

- intent routing
- tool selection
- tool execution
- answer contract
- hallucination guard
- escalation behavior

Claude's job is only to turn structured tool facts into a concise member-facing answer.

## Scope

Update the voice-agent service.

Target node:

```text
compose_answer
# Component 34 - WS-7 Agent Evaluation Harness

> **Workstream**: WS-7 evaluation and safety  
> **Depends on**: Component 33 - WS-7 LangGraph Runtime Tests

## Goal

Add an evaluation harness for the LangGraph voice-agent runtime.

This component should evaluate the actual agent pipeline output, not just a standalone prompt.

It should answer:

- Did the agent choose the right intent?
- Did it call the right tool?
- Did it answer using available facts?
- Did it avoid hallucinated coverage/cost/provider claims?
- Did it escalate when the question was outside scope?
- Is the answer usable for a member phone conversation?

## Scope

Add an eval task for the voice-agent pipeline.

The eval should call:

```text
FinalTranscriptEvent
  -> LangGraph runtime / orchestrate()
  -> AnswerFinalEvent
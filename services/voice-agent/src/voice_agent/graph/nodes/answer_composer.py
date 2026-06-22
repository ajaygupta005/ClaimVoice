"""
Answer composer abstraction (Component 35).

Two implementations behind a common interface:

  MockComposer   — deterministic; requires no API key; used in dev/test.
  ClaudeComposer — calls Anthropic; Claude's only job is to narrate tool
                   facts as a concise phone answer. Claude does NOT choose
                   tools, query databases, or bypass the hallucination guard.

Select via VOICE_AGENT_ANSWER_MODE env var (default: "mock").
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from voice_agent.core.config import settings


# ── I/O contract ──────────────────────────────────────────────────────────────

@dataclass
class ComposerInput:
    question: str
    intent: str
    tool_name: str
    tool_args: dict[str, Any]
    tool_result: str
    member_context: str = ""
    rag_chunks: list[dict[str, Any]] = field(default_factory=list)  # Component 69


@dataclass
class ComposerOutput:
    answer_text: str
    used_facts: list[str] = field(default_factory=list)
    needs_escalation: bool = False
    confidence: float = 1.0
    fallback_reason: str = ""


# ── abstract base ─────────────────────────────────────────────────────────────

class AnswerComposer(ABC):
    @abstractmethod
    def compose(self, inp: ComposerInput) -> ComposerOutput:
        ...


# ── Mock composer (deterministic) ─────────────────────────────────────────────

_ESCALATION_TEXT = (
    "I want to make sure you get the most accurate information. "
    "Let me connect you with a benefits specialist who can answer your question directly."
)


class MockComposer(AnswerComposer):
    """Deterministic answer composer — preserves all pre-C35 behaviour."""

    def compose(self, inp: ComposerInput) -> ComposerOutput:
        intent = inp.intent
        question = inp.question
        result = inp.tool_result

        if intent in ("escalate",):
            return ComposerOutput(
                answer_text=_ESCALATION_TEXT,
                needs_escalation=True,
                confidence=1.0,
            )

        if intent == "help":
            text = (
                "I can help you with your health insurance coverage questions. "
                "You can ask me: whether a service or procedure is covered, "
                "what your copay or deductible is, whether a medication is on your formulary, "
                "or help you find an in-network provider near you. "
                "Just ask your question and I'll look it up in your plan details."
            )
            return ComposerOutput(answer_text=text, confidence=1.0)

        if intent == "coverage":
            match = re.search(
                r"\b(MRI|CT scan|colonoscopy|surgery|physical therapy|urgent care|ER|therapy|X.ray|ultrasound)\b",
                question, re.IGNORECASE,
            )
            service = match.group(0) if match else "the requested service"
            text = (
                f"Yes, {service} is covered under your plan. "
                "Since you have not yet met your deductible, you will pay the negotiated rate "
                "up to your remaining deductible, then your plan covers the rest."
            )
            if re.search(r"\bprior auth\b", result, re.IGNORECASE):
                text += " Prior authorization is required — please have your provider submit a request."
            return ComposerOutput(answer_text=text, used_facts=[result])

        if intent == "cost":
            if "copay" in result:
                text = (
                    "Your in-network copay is $30 for a primary care visit and $75 for urgent care. "
                    "Specialist visits are $50 copay."
                )
            elif "deductible" in result:
                text = (
                    "Your annual deductible is $1,500. You have spent $450 so far this year, "
                    "so you have $1,050 remaining before your plan pays 100%."
                )
            elif "OOP" in result:
                text = (
                    "Your out-of-pocket maximum is $5,000. You have spent $1,200 this year, "
                    "so you have $3,800 remaining."
                )
            else:
                text = (
                    "Based on your plan, the estimated cost for this service is $150 to $250 "
                    "at the negotiated in-network rate, applied toward your deductible."
                )
            return ComposerOutput(answer_text=text, used_facts=[result])

        if intent == "provider":
            match = re.search(
                r"\b(cardiologist|dermatologist|orthopedist|psychiatrist|therapist|specialist|primary care|PCP)\b",
                question, re.IGNORECASE,
            )
            specialty = match.group(0) if match else "provider"
            text = (
                f"I found three in-network {specialty}s near you. "
                "The closest is Dr. Sarah Chen at 425 Madison Ave, accepting new patients. "
                "Would you like me to provide more details or help schedule an appointment?"
            )
            return ComposerOutput(answer_text=text, used_facts=[result])

        if intent == "formulary":
            match = re.search(
                r"\b(lisinopril|metformin|atorvastatin|humira|insulin|ozempic|adderall)\b",
                question, re.IGNORECASE,
            )
            drug = match.group(0) if match else "the medication"
            if "prior authorization" in result:
                text = (
                    f"{drug} is covered as a specialty-tier medication and requires prior authorization. "
                    "Please have your prescriber submit a prior auth request. Allow 3–5 business days."
                )
            else:
                text = (
                    f"Yes, {drug} is on your formulary as a Tier 1 generic. "
                    "Your copay is $10 for a 30-day supply or $25 for a 90-day mail-order supply."
                )
            return ComposerOutput(answer_text=text, used_facts=[result])

        return ComposerOutput(
            answer_text="I'm sorry, I couldn't find a clear answer. Please hold while I connect you with a specialist.",
            needs_escalation=True,
        )


# ── Claude composer ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are the answer narrator for ClaimVoice, an AI phone agent for US health insurance members.

Your job is ONLY to turn structured tool facts and supporting SBC document excerpts into a concise, \
conversational phone answer.

Rules:
- Use ONLY the facts provided in tool_result and sbc_chunks. Do not invent coverage, cost, drug, or provider facts.
- Structured tool_result is the primary source of truth; sbc_chunks are supporting evidence only.
- If sbc_chunks is empty, do not mention citations, documents, or plan text.
- If the tool_result does not contain enough information to answer, set needs_escalation to true.
- Keep the answer brief and phone-friendly (1–3 sentences).
- Do not mention internal systems, tool names, or implementation details.
- Do not use markdown, bullet points, or headers — plain spoken English only.

Respond with valid JSON only. No commentary before or after the JSON.

Required JSON shape:
{
  "answer_text": "<spoken answer string>",
  "used_facts": ["<fact 1>", "<fact 2>"],
  "needs_escalation": false,
  "confidence": 0.95
}
"""

_FALLBACK_ANSWER = (
    "I'm having trouble retrieving that information right now. "
    "Let me connect you with a benefits specialist who can help."
)


class ClaudeComposer(AnswerComposer):
    """
    Calls Anthropic Claude to narrate tool facts as a member-facing phone answer.
    Falls back to _FALLBACK_ANSWER on any API or parse failure.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        import anthropic  # imported lazily — not needed in mock mode
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def compose(self, inp: ComposerInput) -> ComposerOutput:
        if inp.intent == "escalate":
            return ComposerOutput(
                answer_text=_ESCALATION_TEXT,
                needs_escalation=True,
                confidence=1.0,
            )

        if inp.intent == "help":
            return MockComposer().compose(inp)

        sbc_chunks = [
            {"chunkText": c.get("chunk_text", ""), "sectionName": c.get("section_name", "")}
            for c in inp.rag_chunks
            if c.get("chunk_text")
        ]
        user_payload = json.dumps({
            "question": inp.question,
            "intent": inp.intent,
            "tool_name": inp.tool_name,
            "tool_result": inp.tool_result,
            "member_context": inp.member_context or "Silver PPO plan member",
            "sbc_chunks": sbc_chunks,
        }, ensure_ascii=False)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=256,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_payload}],
            )
            raw = response.content[0].text.strip()
            return self._parse(raw)
        except Exception as exc:
            logger.warning(f"ClaudeComposer failed: {exc!r} — falling back to safe answer")
            return ComposerOutput(
                answer_text=_FALLBACK_ANSWER,
                needs_escalation=True,
                fallback_reason=f"claude_error: {type(exc).__name__}",
            )

    def _parse(self, raw: str) -> ComposerOutput:
        # Strip accidental markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(f"ClaudeComposer: JSON parse failed: {exc!r}")
            return ComposerOutput(
                answer_text=_FALLBACK_ANSWER,
                needs_escalation=True,
                fallback_reason=f"json_parse_error: {exc}",
            )

        answer_text = data.get("answer_text", "").strip()
        if not answer_text:
            logger.warning("ClaudeComposer: empty answer_text in response")
            return ComposerOutput(
                answer_text=_FALLBACK_ANSWER,
                needs_escalation=True,
                fallback_reason="empty_answer_text",
            )

        return ComposerOutput(
            answer_text=answer_text,
            used_facts=data.get("used_facts") or [],
            needs_escalation=bool(data.get("needs_escalation", False)),
            confidence=float(data.get("confidence", 1.0)),
        )


# ── factory ───────────────────────────────────────────────────────────────────

def build_composer() -> AnswerComposer:
    """
    Instantiate the correct composer from environment config.
    Called once at graph compile time.
    """
    if settings.voice_agent_answer_mode == "claude":
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "VOICE_AGENT_ANSWER_MODE=claude requires ANTHROPIC_API_KEY to be set."
            )
        logger.info(f"ClaudeComposer initialised (model={settings.anthropic_model})")
        return ClaudeComposer(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    logger.info("MockComposer initialised (VOICE_AGENT_ANSWER_MODE=mock)")
    return MockComposer()

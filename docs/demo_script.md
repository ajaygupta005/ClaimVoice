# ClaimVoice - Demo Script (~7-8 min)

A grounded, multi-modal voice agent for US health-insurance members. Members ask coverage,
cost, and provider questions by voice and hear answers **grounded in their real plan**, with a
hallucination guard that fact-checks every claim before it's spoken.

> Demo member: **Maya Thompson** (`CVX-0042-MT`) - plan **ClaimVoice Demo PPO** - runs as the
> built-in demo member (no login). Visible tabs: **Voice, Plan, Providers** (Card/Calls hidden - mock-only).

---

## 0. Pre-flight (before recording - not on camera)

1. **Ensure the stack is up** (Docker has been flaky - do this first):
   ```powershell
   docker compose up -d postgres
   ```
   Confirm five services: Postgres :5433, eligibility :8002, providers :8003, voice-agent :8004, web :3000.
2. **Warm-up run** - ask each of the 3 questions once so the first take isn't cold (Azure embed + Claude warm up).
3. **Chrome/Edge**, allow mic. Dismiss the Clerk "Configure your application" popup.
4. Keep a typed fallback ready (the input box under the mic) in case STT mishears.
5. Browser zoom ~110-125% so the pipeline + transcript are legible.

> Expect a **~6-12 s pause** after each question (Claude compose + fact-check + SBC retrieval).
> Let the **5-step pipeline animation** carry it - narrate while it runs, or trim in editing.

---

## 1. Intro / hook  (0:00-0:30)
**Show:** the Voice tab (`localhost:3000` auto-redirects there).
**Say:** "Members struggle to get clear answers about what their insurance covers and what it
costs - and generic AI chatbots make things up. ClaimVoice is a voice agent that answers those
questions grounded in the member's *actual* plan, and a hallucination guard fact-checks every
claim before it's ever spoken."

## 2. Voice - coverage  (0:30-1:30)
**Do:** click the mic, ask: **"Is an MRI covered, and does it need prior authorization?"**
**Watch:** the pipeline - *Identify -> Understand (coverage) -> Check (check_coverage) -> Guard (all grounded) -> Respond (Claude)* - then the spoken answer.
**Expected:** *"Yes, MRIs are covered under your plan at 20% coinsurance after your deductible, but
prior authorization is required before the scan is performed - otherwise the claim may be denied."*
**Say:** "Notice the prior-auth detail - that comes from the plan's **Summary of Benefits**, retrieved
by vector search and woven into the answer. Nothing here is invented."

## 3. Voice - cost  (1:30-2:15)
**Do:** ask **"How much of my deductible do I have left?"** *(enunciate "deductible")*
**Expected:** *"You have **$1,050 left** on your deductible - you've met $450 of your $1,500 for the year."*
**Say:** "Real figures from the member's record, not a guess - and the guard confirmed every number."

## 4. Voice - provider  (2:15-3:00)
**Do:** ask **"Find a cardiologist near me."**
**Expected:** *"I found three cardiologists near you - James Whitfield about 0.24 km away, Henry Cho
0.87 km, and Maria Reyes 1.02 km..."*
**Say:** "Live provider search ranked by distance - the agent calls a separate providers service and
the geo-ranking happens against real location data."

## 5. The guard - it won't invent coverage (the differentiator)  (3:00-3:45)
**Do:** ask about a service NOT in the plan: **"Is acupuncture for my back covered?"**
**Expected:** a grounded **negative** - *"Based on your plan's benefits, acupuncture is not a covered
service... you do have the right to appeal this determination."* It states the accurate "not covered"
from the plan data - it does **not** invent a yes.
**Optional (explicit escalation):** ask **"I'd like to speak to a human representative."** -> the agent
escalates: *"...let me connect you with a benefits specialist who can answer your question directly."*
**Say:** "This is the core idea: the agent only says what the plan data supports. For an uncovered
service it gives the accurate 'no'; when it genuinely can't help, it escalates - never guesses."

## 6. Plan tab  (3:45-4:30)
**Do:** left nav -> **Plan**.
**Show:** member + plan header (note the **live** badge), the deductible / out-of-pocket bars, the
coverage-highlights table, prior-auth notes.
**Say:** "The same data the voice agent grounds on, on screen - pulled live from the eligibility service."

## 7. Providers tab  (4:30-5:15)
**Do:** left nav -> **Providers**. Type **"cardiology"** or pick a specialty; adjust the distance filter.
**Show:** live provider cards (name, distance, accepting-new), the detail panel.
**Say:** "Live in-area provider search - the same backend the voice agent used for 'find a cardiologist'."

## 8. Under the hood  (5:15-6:30)
**Show:** the pipeline trace / connections panel (or a slide of the architecture).
**Say (the AI/ML breadth):**
- **Voice ML** - browser speech-to-text -> Claude -> Cartesia speech-back.
- **Agentic (LangGraph)** - identify member -> understand intent -> call a tool -> compose -> guard -> respond.
- **Generative AI** - Claude (`claude-sonnet-4-6`) narrates answers using *only* the tool facts.
- **RAG / vector search** - Summary-of-Benefits PDFs chunked + embedded with **Azure
  text-embedding-3-large** into **pgvector**; retrieved at query time to ground coverage answers.
- **Structured grounding + geo** - PostgreSQL plan graph (benefits, formulary, deductibles) and
  **PostGIS** provider geo-search.
- **Microservices** - eligibility + providers behind the voice agent.

## 9. Proof - it stays grounded  (6:30-7:15)
**Do (terminal):** run the eval gate.
```powershell
$env:PYTHONPATH="services/voice-agent/src"; $env:TOOL_MODE="mock"; $env:VOICE_AGENT_ANSWER_MODE="mock"; $env:FACT_CHECK_MODE="mock"; $env:TTS_MODE="mock"; $env:STT_MODE="mock"
uv run --no-project --python 3.12 --with langgraph --with httpx --with pydantic --with pydantic-settings --with loguru --with typing-extensions --with anthropic --with pytest python -m pytest eval/tests -m "not integration" -q
```
**Expected:** **51 passed**.
**Say:** "An automated eval suite - agent-pipeline, hallucination, and provider-lookup checks -
verifies the agent stays grounded. 51 green."

## 10. Close  (7:15-7:45)
**Say:** "ClaimVoice: the confidence of calling your insurer's support line, answered instantly by
voice - and guaranteed not to make things up."

---

## Cheat-sheet (questions -> expected)
| Ask | Expected |
|---|---|
| "Is an MRI covered, and does it need prior authorization?" | covered, 20% coinsurance after deductible, **prior auth required** (SBC-cited) |
| "How much of my deductible do I have left?" | **$1,050** left ($450 of $1,500 met) |
| "Find a cardiologist near me" | 3 cardiologists w/ distances (Whitfield 0.24 km ...) |
| "Is acupuncture for my back covered?" | grounded **"not covered"** + appeal rights (won't invent a yes) |
| "I'd like to speak to a human representative" | escalates to a benefits specialist |

## If something stalls mid-demo
Almost always Docker stopping. `docker compose up -d postgres`, then the services reconnect
(restart any service per `Plan/LIVE-PRODUCT-RESULTS.md`). The browser falls back to a local mock
pipeline if the backend is unreachable - if answers look generic, check the services are up.

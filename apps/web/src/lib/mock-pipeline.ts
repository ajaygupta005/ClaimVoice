/**
 * Mock agent pipeline for the ClaimVoice voice demo.
 *
 * Simulates the full WS-7 call flow entirely in the browser:
 *   Twilio session → STT → identify member → route intent →
 *   tool call → mock Claude answer → hallucination guard → TTS
 *
 * No real network calls are made. All data is grounded in
 * the Silver PPO 4500 plan facts already in mock-data.ts.
 */

// ── Types ─────────────────────────────────────────────────────────────────────

export type ToolName =
  | 'verify_identity'
  | 'check_coverage'
  | 'estimate_cost'
  | 'find_provider'
  | 'check_formulary'
  | 'escalate_to_human'

export type LedStatus = 'connected' | 'demo' | 'degraded' | 'offline'

export interface BackendStatus {
  label: string
  detail: string
  status: LedStatus
}

export interface ToolResult {
  tool: ToolName
  facts: string[]           // grounding facts used by the hallucination guard
  summary: string           // one-line summary shown in pipeline step detail
}

export interface HallucinationResult {
  passed: boolean
  reason: string
}

export interface PipelineResult {
  /** Mocked Twilio session metadata */
  twilio: {
    provider: 'twilio'
    status: 'mock'
    callSid: string
    streamSid: string
  }
  /** STT transcript (the question that was heard/typed) */
  stt: {
    text: string
    confidence: number
  }
  /** Intent routing decision */
  intent: ToolName
  /** Tool call outcome */
  toolResult: ToolResult
  /** Grounded answer from mock Claude */
  answer: string
  /** Hallucination guard verdict */
  guard: HallucinationResult
  /** TTS status (audio prep simulated) */
  tts: {
    status: 'prepared' | 'error'
    durationEstimateMs: number
  }
  /** Backend connection statuses for the LED rail */
  backends: BackendStatus[]
}

// ── Member context (Maya Thompson, Silver PPO 4500) ───────────────────────────

const MEMBER = {
  name: 'Maya Thompson',
  memberId: 'CVX-0042-MT',
  plan: 'Silver PPO 4500',
  carrier: 'BlueCross BlueShield',
  deductible: 4500_00,        // cents
  deductibleYtd: 450_00,      // cents
  oopMax: 7900_00,
  oopYtd: 450_00,
  pcpCopay: 35_00,
  specialistCopay: 70_00,
  urgentCareCopay: 75_00,
  erCopay: 250_00,
  coinsurance: 20,
}

// ── Intent router ─────────────────────────────────────────────────────────────

const COVERAGE_PATTERNS = [
  /\b(mri|ct scan|pet scan|imaging|x.?ray|mammogram|colonoscopy|outpatient surgery|inpatient|hospital|prior auth|authorization|referral|covered|coverage|annual physical|preventive|telehealth|therapy|mental health|dermatologist|specialist|primary care|pcp|eye exam|vision)\b/i,
]
const COST_PATTERNS = [
  /\b(copay|cost|how much|deductible|coinsurance|owe|pay|price|out.of.pocket|oop)\b/i,
]
const FORMULARY_PATTERNS = [
  /\b(lisinopril|metformin|atorvastatin|formulary|drug|medication|prescription|tier|rx|humira|ozempic|insulin)\b/i,
]
const PROVIDER_PATTERNS = [
  /\b(cardiologist|provider|doctor|near me|find a|specialist near|in.network doctor|physician)\b/i,
]
const ESCALATE_PATTERNS = [
  /\b(claim denied|denial|appeal|dispute|complaint|not covered|refused|grievance|billing error)\b/i,
]

export function routeIntent(question: string): ToolName {
  const q = question.toLowerCase()
  if (ESCALATE_PATTERNS.some(p => p.test(q))) return 'escalate_to_human'
  if (FORMULARY_PATTERNS.some(p => p.test(q)))  return 'check_formulary'
  if (PROVIDER_PATTERNS.some(p => p.test(q)))   return 'find_provider'
  if (COST_PATTERNS.some(p => p.test(q)))       return 'estimate_cost'
  if (COVERAGE_PATTERNS.some(p => p.test(q)))   return 'check_coverage'
  // Unknown → safe escalation
  return 'escalate_to_human'
}

// ── Mock tool adapters ────────────────────────────────────────────────────────

function mockVerifyIdentity(): ToolResult {
  return {
    tool: 'verify_identity',
    facts: [`Member ${MEMBER.memberId} (${MEMBER.name}) verified`, `Plan: ${MEMBER.plan}`],
    summary: `${MEMBER.name} · ${MEMBER.memberId} verified`,
  }
}

function mockCheckCoverage(question: string): ToolResult {
  const q = question.toLowerCase()

  if (/mri|ct scan|advanced imaging/.test(q)) {
    return {
      tool: 'check_coverage',
      facts: [
        'MRI / Advanced Imaging: covered in-network',
        '20% coinsurance after deductible',
        'Prior authorization required',
        `Remaining deductible: $${((MEMBER.deductible - MEMBER.deductibleYtd) / 100).toFixed(0)}`,
      ],
      summary: 'MRI covered · prior auth required · 20% after ded.',
    }
  }
  if (/prior auth|authorization/.test(q)) {
    return {
      tool: 'check_coverage',
      facts: [
        'Prior authorization required for MRI, CT, PET, outpatient surgery, inpatient admission',
        'Provider submits prior auth request to BCBS',
        'Allow 3–5 business days for decision',
      ],
      summary: 'Prior auth required — provider must submit to BCBS',
    }
  }
  if (/telehealth/.test(q)) {
    return {
      tool: 'check_coverage',
      facts: ['Telehealth: $0 copay in-network', 'No prior auth required'],
      summary: 'Telehealth $0 copay in-network',
    }
  }
  if (/mental health|therapy/.test(q)) {
    return {
      tool: 'check_coverage',
      facts: ['Mental health therapy: $40 copay per in-network session', 'No referral required'],
      summary: 'Mental health therapy $40 copay in-network',
    }
  }
  if (/annual physical|preventive/.test(q)) {
    return {
      tool: 'check_coverage',
      facts: ['Annual physical: $0 as preventive care in-network'],
      summary: 'Annual physical $0 in-network (preventive)',
    }
  }
  if (/eye exam|vision/.test(q)) {
    return {
      tool: 'check_coverage',
      facts: ['Annual eye exam: $0 under vision benefit in-network'],
      summary: 'Eye exam $0 under vision benefit',
    }
  }
  if (/dermatologist|referral|specialist/.test(q)) {
    return {
      tool: 'check_coverage',
      facts: [
        'Silver PPO 4500 does not require a PCP referral for specialists',
        'Specialist copay: $70 in-network',
      ],
      summary: 'No referral required — specialist copay $70',
    }
  }
  // generic coverage
  return {
    tool: 'check_coverage',
    facts: [`Plan: ${MEMBER.plan} (${MEMBER.carrier})`, 'In-network coverage applies'],
    summary: 'Coverage verified for your plan',
  }
}

function mockEstimateCost(question: string): ToolResult {
  const q = question.toLowerCase()

  if (/urgent care/.test(q)) {
    return {
      tool: 'estimate_cost',
      facts: [`Urgent care copay: $${MEMBER.urgentCareCopay / 100} in-network`],
      summary: `Urgent care copay $${MEMBER.urgentCareCopay / 100} in-network`,
    }
  }
  if (/emergency|er\b/.test(q)) {
    const oopLeft = (MEMBER.oopMax - MEMBER.oopYtd) / 100
    return {
      tool: 'estimate_cost',
      facts: [
        `ER copay: $${MEMBER.erCopay / 100} after deductible`,
        `Remaining OOP max: $${oopLeft.toFixed(0)}`,
      ],
      summary: `ER $${MEMBER.erCopay / 100} copay after deductible`,
    }
  }
  if (/primary care|pcp/.test(q)) {
    return {
      tool: 'estimate_cost',
      facts: [`PCP copay: $${MEMBER.pcpCopay / 100} in-network`],
      summary: `PCP copay $${MEMBER.pcpCopay / 100} in-network`,
    }
  }
  if (/specialist/.test(q)) {
    return {
      tool: 'estimate_cost',
      facts: [`Specialist copay: $${MEMBER.specialistCopay / 100} in-network`],
      summary: `Specialist copay $${MEMBER.specialistCopay / 100} in-network`,
    }
  }
  if (/deductible/.test(q)) {
    const remaining = (MEMBER.deductible - MEMBER.deductibleYtd) / 100
    return {
      tool: 'estimate_cost',
      facts: [
        `Individual deductible: $${MEMBER.deductible / 100}`,
        `YTD spend: $${MEMBER.deductibleYtd / 100}`,
        `Remaining: $${remaining.toFixed(0)}`,
      ],
      summary: `Deductible $${MEMBER.deductible / 100} · $${remaining.toFixed(0)} remaining`,
    }
  }
  if (/out.of.pocket|oop/.test(q)) {
    const oopLeft = (MEMBER.oopMax - MEMBER.oopYtd) / 100
    return {
      tool: 'estimate_cost',
      facts: [
        `OOP max: $${MEMBER.oopMax / 100}`,
        `YTD: $${MEMBER.oopYtd / 100}`,
        `Remaining: $${oopLeft.toFixed(0)}`,
      ],
      summary: `OOP max $${MEMBER.oopMax / 100} · $${oopLeft.toFixed(0)} remaining`,
    }
  }
  // generic cost
  return {
    tool: 'estimate_cost',
    facts: [
      `PCP copay: $${MEMBER.pcpCopay / 100}`,
      `Specialist copay: $${MEMBER.specialistCopay / 100}`,
      `Coinsurance: ${MEMBER.coinsurance}% after deductible`,
    ],
    summary: 'Cost estimate retrieved from plan benefits',
  }
}

function mockCheckFormulary(question: string): ToolResult {
  const q = question.toLowerCase()

  if (/lisinopril/.test(q)) {
    return {
      tool: 'check_formulary',
      facts: [
        'Lisinopril: on formulary as Tier 1 generic',
        'Copay: $10 per fill in-network',
        'No prior auth required',
        'No step therapy required',
      ],
      summary: 'Lisinopril Tier 1 generic · $10 copay',
    }
  }
  if (/metformin/.test(q)) {
    return {
      tool: 'check_formulary',
      facts: ['Metformin: Tier 1 generic · $10 copay'],
      summary: 'Metformin Tier 1 generic · $10 copay',
    }
  }
  if (/atorvastatin/.test(q)) {
    return {
      tool: 'check_formulary',
      facts: ['Atorvastatin: Tier 1 generic · $10 copay'],
      summary: 'Atorvastatin Tier 1 generic · $10 copay',
    }
  }
  if (/humira/.test(q)) {
    return {
      tool: 'check_formulary',
      facts: [
        'Humira: specialty biologic',
        'Formulary status not confirmed for this demo plan',
        'May require prior authorization and step therapy',
      ],
      summary: 'Humira — specialty tier, prior auth may apply',
    }
  }
  // generic formulary
  return {
    tool: 'check_formulary',
    facts: ['Formulary lookup completed', 'Tier 1 generics: $10 · Tier 2: $35 · Tier 3: $70'],
    summary: 'Formulary search completed',
  }
}

function mockFindProvider(question: string): ToolResult {
  const q = question.toLowerCase()
  const specialty = /cardiolog/.test(q) ? 'Cardiology'
    : /dermatolog/.test(q) ? 'Dermatology'
    : /psychiatr|mental health/.test(q) ? 'Psychiatry'
    : /ophthalmolog|eye/.test(q) ? 'Ophthalmology'
    : /orthoped/.test(q) ? 'Orthopedic Surgery'
    : /primary care|pcp|internist/.test(q) ? 'Internal Medicine'
    : 'specialist'

  const providers: Record<string, string> = {
    Cardiology:        'Dr. James Osei — 520 E 70th St, Upper East Side · (212) 555-0144',
    Dermatology:       'Dr. Sofia Reyes — 245 E 54th St, Sutton Place (waitlist only)',
    Psychiatry:        'Dr. Priya Nair — 150 W 55th St, Midtown West · $40 copay',
    Ophthalmology:     'Dr. Leo Marchetti — 30 E 40th St, Murray Hill · eye exam $0',
    'Orthopedic Surgery': 'Dr. Marcus Webb — 333 E 38th St, Murray Hill · prior auth for surgery',
    'Internal Medicine':  'Dr. Rachel Kim — 425 Madison Ave, Midtown East · same-day available',
  }

  const topResult = providers[specialty] ?? 'Several in-network providers found near Midtown, NY'

  return {
    tool: 'find_provider',
    facts: [
      `Specialty: ${specialty}`,
      `In-network providers found near Midtown, New York`,
      topResult,
    ],
    summary: `${specialty} search · top result found in-network`,
  }
}

function mockEscalateToHuman(): ToolResult {
  return {
    tool: 'escalate_to_human',
    facts: [
      'Question requires human specialist review',
      'Claim decisions, appeals, and billing disputes are outside AI scope',
    ],
    summary: 'Escalating to human benefits specialist',
  }
}

// ── Mock Claude answer ────────────────────────────────────────────────────────

function mockClaudeAnswer(question: string, tool: ToolResult): string {
  const q = question.toLowerCase()

  if (tool.tool === 'escalate_to_human') {
    return "I can see your plan details, but this type of question requires a human benefits specialist. I'll transfer you now — typical wait time is under 2 minutes."
  }
  if (tool.tool === 'check_coverage') {
    if (/mri|ct scan|advanced imaging/.test(q)) {
      return `Yes, MRI is covered under your ${MEMBER.plan}. Since you have not met your deductible, you would pay the negotiated rate up to your remaining $${((MEMBER.deductible - MEMBER.deductibleYtd) / 100).toFixed(0)} deductible. Prior authorization is required — your provider needs to submit the request to ${MEMBER.carrier} before scheduling. Allow 3–5 business days.`
    }
    if (/prior auth|authorization/.test(q)) {
      return `Yes, your plan requires prior authorization for advanced imaging, outpatient surgery, and inpatient admissions. Your provider submits the request to ${MEMBER.carrier} before scheduling. Allow 3–5 business days for a decision.`
    }
    if (/telehealth/.test(q)) {
      return `Yes, telehealth visits are covered at $0 copay in-network under your ${MEMBER.plan}.`
    }
    if (/mental health|therapy/.test(q)) {
      return `Yes, mental health therapy is covered. Your in-network copay is $40 per session. No referral is required.`
    }
    if (/annual physical|preventive/.test(q)) {
      return `Yes, your annual physical is covered at $0 as preventive care when seen by an in-network provider under your ${MEMBER.plan}.`
    }
    if (/eye exam|vision/.test(q)) {
      return `Yes, one annual eye exam is covered at $0 under your vision benefit when seen in-network.`
    }
    if (/dermatologist|referral|specialist/.test(q)) {
      return `Your ${MEMBER.plan} does not require a PCP referral for specialists. You can book directly with an in-network dermatologist. Your specialist copay is $70.`
    }
    return `That service is covered under your ${MEMBER.plan}. ${tool.facts[0] ?? ''}`
  }
  if (tool.tool === 'estimate_cost') {
    if (/urgent care/.test(q)) {
      return `Your in-network urgent care copay is $${MEMBER.urgentCareCopay / 100} per visit under your ${MEMBER.plan}.`
    }
    if (/emergency|er\b/.test(q)) {
      return `Your emergency room copay is $${MEMBER.erCopay / 100} after your deductible. You have $${((MEMBER.oopMax - MEMBER.oopYtd) / 100).toFixed(0)} remaining on your out-of-pocket maximum.`
    }
    if (/primary care|pcp/.test(q)) {
      return `Your in-network primary care copay is $${MEMBER.pcpCopay / 100} per visit.`
    }
    if (/specialist/.test(q)) {
      return `Your in-network specialist copay is $${MEMBER.specialistCopay / 100} per visit.`
    }
    if (/deductible/.test(q)) {
      const remaining = (MEMBER.deductible - MEMBER.deductibleYtd) / 100
      return `Your individual deductible is $${MEMBER.deductible / 100}. You have spent $${MEMBER.deductibleYtd / 100} so far this year, leaving $${remaining.toFixed(0)} remaining.`
    }
    if (/out.of.pocket|oop/.test(q)) {
      const oopLeft = (MEMBER.oopMax - MEMBER.oopYtd) / 100
      return `Your out-of-pocket maximum is $${MEMBER.oopMax / 100}. You have $${oopLeft.toFixed(0)} remaining before it is met.`
    }
    return `Based on your ${MEMBER.plan}: ${tool.summary}.`
  }
  if (tool.tool === 'check_formulary') {
    if (/lisinopril/.test(q)) {
      return `Yes, lisinopril is on your formulary as a Tier 1 generic. Your copay is $10 per fill. No prior authorization or step therapy is required.`
    }
    if (/metformin/.test(q)) {
      return `Yes, metformin is on your formulary as a Tier 1 generic at $10 per fill.`
    }
    if (/humira/.test(q)) {
      return `Humira is a specialty biologic that may require prior authorization and step therapy on your plan. I recommend contacting ${MEMBER.carrier} member services to confirm your specific formulary status.`
    }
    return `Formulary lookup complete: ${tool.summary}.`
  }
  if (tool.tool === 'find_provider') {
    const q2 = question.toLowerCase()
    const specialty = /cardiolog/.test(q2) ? 'cardiologists'
      : /dermatolog/.test(q2) ? 'dermatologists'
      : /psychiatr|mental health/.test(q2) ? 'psychiatrists'
      : 'in-network specialists'
    const top = tool.facts[2] ?? 'in-network providers found'
    return `I found ${specialty} in your network near Midtown, New York. Top result: ${top}. Would you like me to provide directions or contact information?`
  }
  return `Based on your ${MEMBER.plan}: ${tool.summary}.`
}

// ── Hallucination guard ───────────────────────────────────────────────────────

export function mockHallucinationGuard(
  answer: string,
  toolResult: ToolResult,
): HallucinationResult {
  if (toolResult.tool === 'escalate_to_human') {
    return { passed: true, reason: 'Escalation answer does not contain plan-specific claims.' }
  }

  // Check that the answer doesn't introduce claims absent from the tool facts
  const joinedFacts = toolResult.facts.join(' ').toLowerCase()
  const answerLower = answer.toLowerCase()

  // Look for dollar amounts in the answer and verify each is in the facts
  const dollarMatches = answerLower.match(/\$[\d,]+/g) ?? []
  for (const amt of dollarMatches) {
    if (!joinedFacts.includes(amt.replace(',', ''))) {
      return { passed: false, reason: `Amount ${amt} in answer not found in tool facts.` }
    }
  }

  return { passed: true, reason: 'All claims grounded in plan data — no hallucinations detected.' }
}

// ── TTS adapter ───────────────────────────────────────────────────────────────

function mockTts(answer: string): { status: 'prepared' | 'error'; durationEstimateMs: number } {
  if (!answer.trim()) return { status: 'error', durationEstimateMs: 0 }
  const wordCount = answer.split(/\s+/).length
  return { status: 'prepared', durationEstimateMs: Math.round(wordCount * 400) }
}

// ── Backend statuses ──────────────────────────────────────────────────────────

function buildBackendStatuses(guard: HallucinationResult): BackendStatus[] {
  return [
    { label: 'Voice Agent API',     detail: 'localhost:8004',          status: 'demo' },
    { label: 'STT',                 detail: 'Deepgram Nova-2',         status: 'demo' },
    { label: 'TTS',                 detail: 'Cartesia Sonic',          status: 'demo' },
    { label: 'Hallucination guard', detail: guard.passed ? 'passed' : 'FAILED', status: guard.passed ? 'demo' : 'degraded' },
    { label: 'Telephony bridge',    detail: 'Twilio Media Streams',    status: 'demo' },
  ]
}

// ── Rotating demo SIDs ────────────────────────────────────────────────────────

let _callSeq = 1
function nextSids() {
  const n = String(_callSeq++).padStart(3, '0')
  return { callSid: `CA-demo-${n}`, streamSid: `MZ-demo-${n}` }
}

// ── Public entry point ────────────────────────────────────────────────────────

/**
 * Run the full mock pipeline for a given question (typed or simulated voice).
 * Returns a `PipelineResult` with all intermediate outputs wired together.
 */
export function runMockPipeline(question: string): PipelineResult {
  const sids = nextSids()

  const stt = {
    text: question,
    confidence: question.startsWith('(voice') ? 0.87 : 1.0,
  }

  const intent = routeIntent(question)

  const toolResult: ToolResult =
    intent === 'verify_identity'   ? mockVerifyIdentity() :
    intent === 'check_coverage'    ? mockCheckCoverage(question) :
    intent === 'estimate_cost'     ? mockEstimateCost(question) :
    intent === 'check_formulary'   ? mockCheckFormulary(question) :
    intent === 'find_provider'     ? mockFindProvider(question) :
                                     mockEscalateToHuman()

  const answer  = mockClaudeAnswer(question, toolResult)
  const guard   = mockHallucinationGuard(answer, toolResult)
  const tts     = mockTts(answer)

  return {
    twilio: { provider: 'twilio', status: 'mock', ...sids },
    stt,
    intent,
    toolResult,
    answer,
    guard,
    tts,
    backends: buildBackendStatuses(guard),
  }
}

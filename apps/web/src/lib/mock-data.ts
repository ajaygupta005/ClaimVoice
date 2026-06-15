// ── Call history (Component 22) ──────────────────────────────────────────────

export type CallStatus = 'completed' | 'no_answer' | 'transferred' | 'in_progress'
export type ConsentStatus = 'recorded_with_consent' | 'not_recorded' | 'pending'

export interface CallRecord {
  id: string
  memberId: string
  memberName: string
  phone: string
  dateIso: string          // ISO 8601
  durationSec: number
  status: CallStatus
  consentStatus: ConsentStatus
  mainQuestion: string
  assistantSummary: string
  transcript: VoiceTurn[]
  toolOutcome?: string
}

export const mockCallHistory: CallRecord[] = [
  {
    id: 'CALL-0041',
    memberId: 'CVX-0042-MT', memberName: 'Maya Thompson', phone: '+12125550101',
    dateIso: '2026-06-13T14:22:00Z', durationSec: 187, status: 'completed',
    consentStatus: 'recorded_with_consent',
    mainQuestion: 'Is an MRI of the brain covered?',
    assistantSummary: 'Confirmed MRI coverage with prior auth requirement. Member notified of $4,050 remaining deductible.',
    toolOutcome: 'check_coverage → fact_check passed',
    transcript: [
      { id: 'c41-1', role: 'member',    text: 'Is an MRI of the brain covered under my plan?',  timestampMs: 0 },
      { id: 'c41-2', role: 'assistant', text: 'Yes, MRI is covered. Since you have not met your deductible, you would pay the negotiated rate up to your remaining $4,050 deductible. Prior authorization is required.', timestampMs: 3000 },
      { id: 'c41-3', role: 'member',    text: 'How do I get prior authorization?',               timestampMs: 9000 },
      { id: 'c41-4', role: 'assistant', text: 'Your provider submits the prior auth request to BlueCross BlueShield before scheduling. Allow 3–5 business days for a decision.', timestampMs: 12000 },
    ],
  },
  {
    id: 'CALL-0040',
    memberId: 'CVX-0042-MT', memberName: 'Maya Thompson', phone: '+12125550101',
    dateIso: '2026-06-10T09:05:00Z', durationSec: 94, status: 'completed',
    consentStatus: 'recorded_with_consent',
    mainQuestion: 'What is my urgent care copay?',
    assistantSummary: 'Confirmed $75 urgent care copay. Member asked about nearest urgent care location.',
    toolOutcome: 'check_coverage → find_provider → fact_check passed',
    transcript: [
      { id: 'c40-1', role: 'member',    text: 'What is my urgent care copay?',                  timestampMs: 0 },
      { id: 'c40-2', role: 'assistant', text: 'Your in-network urgent care copay is $75 per visit.', timestampMs: 2500 },
      { id: 'c40-3', role: 'member',    text: 'Is there an urgent care near Midtown?',           timestampMs: 7000 },
      { id: 'c40-4', role: 'assistant', text: 'Yes, there are several in-network urgent care centers near Midtown Manhattan. The closest is at 425 Madison Ave.', timestampMs: 10000 },
    ],
  },
  {
    id: 'CALL-0039',
    memberId: 'CVX-0042-MT', memberName: 'Maya Thompson', phone: '+12125550101',
    dateIso: '2026-06-07T16:41:00Z', durationSec: 312, status: 'transferred',
    consentStatus: 'recorded_with_consent',
    mainQuestion: 'Why was my claim denied?',
    assistantSummary: 'Claim denial query outside AI scope. Escalated to human agent after 5 minutes.',
    toolOutcome: 'escalate_to_human',
    transcript: [
      { id: 'c39-1', role: 'member',    text: 'I got a letter saying my claim was denied. Can you help?', timestampMs: 0 },
      { id: 'c39-2', role: 'assistant', text: 'I can see your plan details, but claim-specific decisions require a human agent. I\'ll transfer you now.', timestampMs: 4000 },
    ],
  },
  {
    id: 'CALL-0038',
    memberId: 'CVX-0042-MT', memberName: 'Maya Thompson', phone: '+12125550101',
    dateIso: '2026-05-28T11:15:00Z', durationSec: 55, status: 'no_answer',
    consentStatus: 'not_recorded',
    mainQuestion: '—',
    assistantSummary: 'Outbound callback attempt. No answer.',
    transcript: [],
  },
]

// ── Voice assistant (Component 21) ───────────────────────────────────────────

export type TurnRole = 'member' | 'assistant'

export interface VoiceTurn {
  id: string
  role: TurnRole
  text: string
  timestampMs: number   // ms offset from session start for display
}

export type ToolStage =
  | 'identify_member'
  | 'check_coverage'
  | 'find_provider'
  | 'fact_check'
  | 'done'

export interface ToolCall {
  stage: ToolStage
  label: string
  detail: string
  status: 'completed' | 'running' | 'pending'
}

export const mockVoiceTranscript: VoiceTurn[] = [
  { id: 't1', role: 'member',    text: 'Is an MRI of the brain covered under my plan?',            timestampMs:  1000 },
  { id: 't2', role: 'assistant', text: 'Yes, MRI is covered. Since you have not met your deductible, you would pay the negotiated rate up to your remaining $4,050 deductible. Prior authorization is required — your provider needs to submit the request to BlueCross BlueShield before scheduling.',  timestampMs:  4200 },
  { id: 't3', role: 'member',    text: 'What is my copay for a primary care visit?',                timestampMs: 12000 },
  { id: 't4', role: 'assistant', text: 'Your in-network primary care copay is $35 per visit under your Silver PPO 4500 plan.',  timestampMs: 14500 },
  { id: 't5', role: 'member',    text: 'Is lisinopril covered on my formulary?',                    timestampMs: 22000 },
  { id: 't6', role: 'assistant', text: 'Yes, lisinopril is on your formulary as a Tier 1 generic. Your copay is $10 per fill.',  timestampMs: 24800 },
]

export const mockLatestAnswer: VoiceTurn = mockVoiceTranscript[mockVoiceTranscript.length - 1]

export const mockToolStages: ToolCall[] = [
  { stage: 'identify_member', label: 'Identify member',   detail: 'Maya Thompson · CVX-0042-MT verified',          status: 'completed' },
  { stage: 'check_coverage',  label: 'Check coverage',    detail: 'Formulary lookup · Tier 1 generic confirmed',   status: 'completed' },
  { stage: 'find_provider',   label: 'Find provider',     detail: 'Not required for formulary query',              status: 'completed' },
  { stage: 'fact_check',      label: 'Hallucination guard', detail: 'Answer grounded in plan data · no flags',     status: 'completed' },
]

export type VoiceStatus =
  | 'ready'
  | 'listening'
  | 'finalizing_stt'
  | 'thinking'
  | 'speaking'
  | 'error_recoverable'

// ── Provider search (Component 20) ───────────────────────────────────────────

export interface Provider {
  id: string
  name: string
  specialty: string
  subspecialty?: string
  distanceMi: number
  inNetwork: boolean
  acceptingPatients: boolean
  rating: number       // 1–5
  reviewCount: number
  address: string
  neighborhood: string
  phone: string
  npi: string
  note?: string
  lat: number
  lng: number
}

export const mockProviders: Provider[] = [
  {
    id: 'p1', name: 'Dr. Rachel Kim', specialty: 'Internal Medicine', subspecialty: 'Primary Care',
    distanceMi: 0.4, inNetwork: true, acceptingPatients: true, rating: 4.8, reviewCount: 312,
    address: '425 Madison Ave, New York, NY 10017', neighborhood: 'Midtown East',
    phone: '(212) 555-0101', npi: '1234567890',
    note: 'Same-day appointments available. Telehealth offered.',
    lat: 40.7563, lng: -73.9763,
  },
  {
    id: 'p2', name: 'Dr. James Osei', specialty: 'Cardiology',
    distanceMi: 0.9, inNetwork: true, acceptingPatients: true, rating: 4.6, reviewCount: 184,
    address: '520 East 70th St, New York, NY 10021', neighborhood: 'Upper East Side',
    phone: '(212) 555-0144', npi: '1234567891',
    note: 'Affiliated with Weill Cornell Medicine.',
    lat: 40.7678, lng: -73.9540,
  },
  {
    id: 'p3', name: 'Dr. Sofia Reyes', specialty: 'Dermatology',
    distanceMi: 1.1, inNetwork: true, acceptingPatients: false, rating: 4.9, reviewCount: 541,
    address: '245 E 54th St, New York, NY 10022', neighborhood: 'Sutton Place',
    phone: '(212) 555-0178', npi: '1234567892',
    note: 'Not accepting new patients. Waitlist available.',
    lat: 40.7572, lng: -73.9631,
  },
  {
    id: 'p4', name: 'Dr. Marcus Webb', specialty: 'Orthopedic Surgery',
    distanceMi: 1.4, inNetwork: true, acceptingPatients: true, rating: 4.5, reviewCount: 209,
    address: '333 East 38th St, New York, NY 10016', neighborhood: 'Murray Hill',
    phone: '(212) 555-0222', npi: '1234567893',
    note: 'Prior auth required for surgical consults.',
    lat: 40.7476, lng: -73.9738,
  },
  {
    id: 'p5', name: 'Dr. Priya Nair', specialty: 'Psychiatry', subspecialty: 'Adult Mental Health',
    distanceMi: 0.7, inNetwork: true, acceptingPatients: true, rating: 4.7, reviewCount: 97,
    address: '150 W 55th St, New York, NY 10019', neighborhood: 'Midtown West',
    phone: '(212) 555-0255', npi: '1234567894',
    note: 'Telehealth and in-person available. $40 copay.',
    lat: 40.7637, lng: -73.9800,
  },
  {
    id: 'p6', name: 'Dr. Thomas Chen', specialty: 'Radiology', subspecialty: 'Advanced Imaging',
    distanceMi: 2.1, inNetwork: false, acceptingPatients: true, rating: 4.3, reviewCount: 56,
    address: '10 Union Square East, New York, NY 10003', neighborhood: 'Union Square',
    phone: '(212) 555-0288', npi: '1234567895',
    note: 'Out-of-network — 50% coinsurance applies. Prior auth required.',
    lat: 40.7357, lng: -73.9911,
  },
  {
    id: 'p7', name: 'Dr. Amara Johnson', specialty: 'Obstetrics & Gynecology',
    distanceMi: 1.6, inNetwork: true, acceptingPatients: true, rating: 4.8, reviewCount: 421,
    address: '115 East 57th St, New York, NY 10022', neighborhood: 'Midtown East',
    phone: '(212) 555-0311', npi: '1234567896',
    note: 'Maternity care fully covered under your PPO.',
    lat: 40.7604, lng: -73.9697,
  },
  {
    id: 'p8', name: 'Dr. Leo Marchetti', specialty: 'Ophthalmology',
    distanceMi: 0.6, inNetwork: true, acceptingPatients: true, rating: 4.4, reviewCount: 133,
    address: '30 East 40th St, New York, NY 10016', neighborhood: 'Murray Hill',
    phone: '(212) 555-0344', npi: '1234567897',
    note: 'Annual eye exam covered at $0 under vision benefit.',
    lat: 40.7516, lng: -73.9803,
  },
]

export const SPECIALTIES = [
  'All specialties',
  'Internal Medicine',
  'Cardiology',
  'Dermatology',
  'Orthopedic Surgery',
  'Psychiatry',
  'Radiology',
  'Obstetrics & Gynecology',
  'Ophthalmology',
]

// ── Member (reused by Sidebar / other components) ─────────────────────────────

export const mockMember = {
  name: 'Maya Thompson',
  plan: 'Silver PPO 4500',
  status: 'Active' as const,
  memberId: 'CVX-0042-MT',
}

export type FieldStatus = 'confirmed' | 'review' | 'missing'

export interface ExtractedField {
  label: string
  value: string
  confidence: number   // 0–100
  source: string
  status: FieldStatus
}

// ── Plan details (Component 19) ───────────────────────────────────────────────

export const mockPlan = {
  planName: 'Silver PPO 4500',
  carrier: 'BlueCross BlueShield',
  planType: 'PPO',
  metalLevel: 'Silver',
  planYear: 2026,
  groupNumber: 'GRP-7734',
  effectiveDate: '01/01/2026',
  network: 'Blue PPO Broad',
}

export interface CostSummary {
  label: string
  value: string
  used?: string
  max?: string
  note?: string
}

export const mockCostSummary: CostSummary[] = [
  { label: 'Individual Deductible', value: '$4,500', used: '$450',  max: '$4,500', note: 'In-network' },
  { label: 'Out-of-Pocket Max',     value: '$7,900', used: '$450',  max: '$7,900', note: 'In-network' },
  { label: 'PCP Copay',             value: '$35',                               note: 'Per visit' },
  { label: 'Specialist Copay',      value: '$70',                               note: 'Per visit' },
  { label: 'Urgent Care Copay',     value: '$75',                               note: 'Per visit' },
  { label: 'Emergency Room',        value: '$250',                              note: 'After deductible' },
  { label: 'Coinsurance',           value: '20%',                               note: 'After deductible, in-network' },
]

export interface CoverageRow {
  service: string
  inNetwork: string
  outOfNetwork: string
  requiresPriorAuth: boolean
}

export const mockCoverageHighlights: CoverageRow[] = [
  { service: 'Annual Physical',        inNetwork: '$0 (preventive)',  outOfNetwork: '50% after ded.', requiresPriorAuth: false },
  { service: 'Primary Care Visit',     inNetwork: '$35 copay',        outOfNetwork: '50% after ded.', requiresPriorAuth: false },
  { service: 'Specialist Visit',       inNetwork: '$70 copay',        outOfNetwork: '50% after ded.', requiresPriorAuth: false },
  { service: 'Telehealth',             inNetwork: '$0 copay',         outOfNetwork: 'Not covered',    requiresPriorAuth: false },
  { service: 'Mental Health Therapy',  inNetwork: '$40 copay',        outOfNetwork: '50% after ded.', requiresPriorAuth: false },
  { service: 'MRI / Advanced Imaging', inNetwork: '20% after ded.',   outOfNetwork: '50% after ded.', requiresPriorAuth: true  },
  { service: 'Outpatient Surgery',     inNetwork: '20% after ded.',   outOfNetwork: '50% after ded.', requiresPriorAuth: true  },
  { service: 'Inpatient Hospital',     inNetwork: '20% after ded.',   outOfNetwork: '50% after ded.', requiresPriorAuth: true  },
  { service: 'Emergency Room',         inNetwork: '$250 after ded.',  outOfNetwork: '$250 after ded.', requiresPriorAuth: false },
  { service: 'Maternity Care',         inNetwork: '20% after ded.',   outOfNetwork: '50% after ded.', requiresPriorAuth: false },
  { service: 'Prescription – Tier 1',  inNetwork: '$10 copay',        outOfNetwork: 'Not covered',    requiresPriorAuth: false },
  { service: 'Prescription – Tier 2',  inNetwork: '$35 copay',        outOfNetwork: 'Not covered',    requiresPriorAuth: false },
  { service: 'Prescription – Tier 3',  inNetwork: '$70 copay',        outOfNetwork: 'Not covered',    requiresPriorAuth: true  },
  { service: 'Annual Eye Exam',        inNetwork: '$0 (vision)',       outOfNetwork: 'Not covered',    requiresPriorAuth: false },
  { service: 'Dental Cleaning',        inNetwork: 'Not covered',      outOfNetwork: 'Not covered',    requiresPriorAuth: false },
]

export const mockPriorAuthNotes = [
  'MRI, CT scans, and PET scans require prior authorization from BCBS before scheduling.',
  'Inpatient hospital admissions (non-emergency) require prior authorization.',
  'Outpatient surgery at an ambulatory surgery center requires prior authorization.',
  'Tier 3 specialty medications require prior authorization and step therapy documentation.',
  'Home health care and durable medical equipment (DME) over $500 require prior authorization.',
]

export const mockExampleQuestions = [
  { q: 'Is an MRI of the brain covered?',            hint: 'Imaging / prior auth' },
  { q: 'What is my copay for a primary care visit?', hint: 'Copay' },
  { q: 'How much will my next ER visit cost?',       hint: 'Emergency' },
  { q: 'Is lisinopril on my formulary?',             hint: 'Pharmacy' },
  { q: 'Can I see a dermatologist without a referral?', hint: 'Referral' },
  { q: 'Is therapy covered?',                        hint: 'Mental health' },
  { q: 'Is my annual physical free?',                hint: 'Preventive' },
  { q: 'Are telehealth visits covered?',             hint: 'Telehealth' },
]

// ── Card extraction fields (Component 18) ────────────────────────────────────

export const mockExtractedFields: ExtractedField[] = [
  { label: 'Member ID',       value: 'CVX-0042-MT',    confidence: 98, source: 'LayoutLMv3', status: 'confirmed' },
  { label: 'Member Name',     value: 'Maya Thompson',  confidence: 96, source: 'LayoutLMv3', status: 'confirmed' },
  { label: 'Group Number',    value: 'GRP-7734',       confidence: 91, source: 'LayoutLMv3', status: 'confirmed' },
  { label: 'Plan Name',       value: 'Silver PPO 4500', confidence: 94, source: 'Claude',    status: 'confirmed' },
  { label: 'Carrier',         value: 'BlueCross BlueShield', confidence: 88, source: 'ResNet-50', status: 'review' },
  { label: 'RX BIN',          value: '610415',         confidence: 82, source: 'LayoutLMv3', status: 'review' },
  { label: 'RX PCN',          value: 'BCBSRX',         confidence: 85, source: 'LayoutLMv3', status: 'review' },
  { label: 'Effective Date',  value: '01/01/2026',     confidence: 0,  source: '—',           status: 'missing' },
]

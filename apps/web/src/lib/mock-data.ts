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

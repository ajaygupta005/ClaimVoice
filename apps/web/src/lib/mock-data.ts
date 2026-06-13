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

// Two-party-consent states require an announcement before recording.
// Reference: federal one-party-consent default, plus the 12 two-party states.

const TWO_PARTY_STATES = new Set([
  'CA', 'CT', 'DE', 'FL', 'IL', 'MD', 'MA', 'MT', 'NH', 'OR', 'PA', 'WA',
])

// Subset of NANPA area code -> state. Covers most major metros. Expand to
// the full list from nationalnanpa.com later if needed.
const AREA_CODE_TO_STATE: Record<string, string> = {
  '212': 'NY', '213': 'CA', '214': 'TX', '215': 'PA', '216': 'OH',
  '301': 'MD', '302': 'DE', '303': 'CO', '305': 'FL', '310': 'CA',
  '312': 'IL', '313': 'MI', '314': 'MO', '315': 'NY', '317': 'IN',
  '321': 'FL', '323': 'CA', '401': 'RI', '404': 'GA', '407': 'FL',
  '408': 'CA', '410': 'MD', '412': 'PA', '413': 'MA', '415': 'CA',
  '425': 'WA', '443': 'MD', '484': 'PA', '503': 'OR', '508': 'MA',
  '510': 'CA', '512': 'TX', '516': 'NY', '561': 'FL', '562': 'CA',
  '585': 'NY', '602': 'AZ', '603': 'NH', '607': 'NY', '610': 'PA',
  '614': 'OH', '617': 'MA', '619': 'CA', '626': 'CA', '631': 'NY',
  '646': 'NY', '650': 'CA', '703': 'VA', '707': 'CA', '708': 'IL',
  '713': 'TX', '714': 'CA', '717': 'PA', '718': 'NY', '770': 'GA',
  '773': 'IL', '781': 'MA', '786': 'FL', '805': 'CA', '813': 'FL',
  '814': 'PA', '818': 'CA', '857': 'MA', '858': 'CA', '860': 'CT',
  '908': 'NJ', '917': 'NY', '919': 'NC', '925': 'CA', '949': 'CA',
  '954': 'FL', '973': 'NJ',
}

export function getStateFromPhone(phone: string): string | null {
  const cleaned = phone.replace(/\D/g, '')
  let areaCode: string
  if (cleaned.length === 11 && cleaned.startsWith('1')) areaCode = cleaned.slice(1, 4)
  else if (cleaned.length === 10) areaCode = cleaned.slice(0, 3)
  else return null
  return AREA_CODE_TO_STATE[areaCode] ?? null
}

export function requiresTwoPartyConsent(phone: string): boolean {
  const state = getStateFromPhone(phone)
  // If we cannot determine state, default to safer behavior (play the prompt).
  if (!state) return true
  return TWO_PARTY_STATES.has(state)
}

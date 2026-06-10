// Used by services/document-ai. Extracts structured fields from a US health
// insurance card image.

export const cardExtractionPrompt = `
You are reading a US health insurance card. Look at the image and return the
following fields as JSON:

- member_id (alphanumeric, 6-15 chars)
- name (full name on the card)
- date_of_birth (YYYY-MM-DD if present)
- group_number
- plan_name
- effective_date
- expiration_date
- phone_number (member services line)
- carrier_name
- rx_bin
- rx_pcn
- rx_group

Use null for any field that is not visible. Do not guess.
`.trim()

// changelog:
// v1 - initial version

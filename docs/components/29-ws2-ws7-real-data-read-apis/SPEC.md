# Component 29 - WS-2/WS-7 Real Data Read APIs

> **Workstream**: WS-2 + WS-7 shared data surface  
> **Depends on**: Data Layer, WS-2 UI shell, WS-7 voice-agent loop

## Goal

Expose the real ingested insurance data through small read-only APIs so both the dashboard UI and telephone AI can stop depending on hardcoded mock data.

This component does not replace the UI yet and does not add Claude/LangGraph orchestration. It creates the stable service layer that the next UI and voice-agent components will call.

## What This Component Does

Add read endpoints over the existing Postgres schema:

- member + plan summary
- plan benefits
- formulary lookup
- provider search
- provider detail

Use existing tables:

- `members`
- `plans`
- `plan_benefits`
- `formulary_drug`
- `providers`
- `in_network` where useful

## Eligibility Service APIs

Add routes under `services/eligibility`:

### `GET /api/v1/members/{member_id}/summary`

Returns member eligibility and plan context.

Response shape:

```json
{
  "member": {
    "memberId": "CVX-0042-MT",
    "name": "Maya Thompson",
    "eligibilityStatus": "active",
    "deductibleYtdCents": 45000,
    "oopYtdCents": 45000
  },
  "plan": {
    "id": "uuid",
    "name": "Silver PPO 4500",
    "issuer": "BlueCross BlueShield",
    "year": 2026,
    "type": "PPO",
    "metalLevel": "Silver",
    "hsaEligible": false,
    "state": "NY"
  }
}
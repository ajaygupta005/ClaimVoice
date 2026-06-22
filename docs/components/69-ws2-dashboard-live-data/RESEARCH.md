# Component 69 - WS-2 Dashboard Live Data - Research

## Why useState(mock) + useEffect-replace (graceful fallback)
Seeding state with the existing mock fixtures and replacing it on a successful fetch means
the tab always renders -- live when the backend is up, mock when it isn't -- with no loading
flash and no hard dependency on the services being up. This kept the change low-risk and
verifiable by typecheck without a browser.

## Why the providers proxy needs an extra path segment
Eligibility endpoints live at `/api/v1/<resource>` (coverage, members, ...) while providers
live at `/api/v1/providers/<resource>` (near, bulk). A single generic catch-all that maps
`/api/<svc>/<slug>` -> `/api/v1/<slug>` works for eligibility but sent `/api/providers/near`
-> `/api/v1/near` (404), so the Providers tab silently fell back to mock. The providers
proxy prepends `providers/`. (Caught during the warm-up dry run.)

## Why raise the respond proxy timeout
The browser respond proxy aborted at 10s, but Claude compose + fact-check + SBC retrieval
take ~6-12s, so the proxy returned 503 and the client fell back to its local mock pipeline.
30s lets the real grounded answer through.

# Component 65 - WS-1 Dedicated Live Database - Research

## Why a dedicated :5433 instance (not reuse)
The earlier dev DB reused another app's plain `postgres:16-alpine` -- no PostGIS, no
pgvector -- which forced app-side Haversine and deferred SBC RAG. The live product needs
both extensions, so we run our own image. Port 5432 is taken by the other app; 5433 is
free, so the two databases coexist on the box.

## Why the combined PostGIS + pgvector image
Provider geo (WS-5) needs PostGIS; SBC RAG (WS-4) needs pgvector. The stock images ship one
or the other, so `infra/postgres/Dockerfile` is `postgis/postgis:16-3.4` plus the
`postgresql-16-pgvector` package -- one image, both extensions, so a single Postgres backs
the whole product.

## Why seed cardiology separately
The synthetic NPPES sample has no cardiology taxonomy, so "find a cardiologist" honestly
returned "none found". A small idempotent SQL seed adds cardiology providers near the demo
member's coordinates with `specialty_codes` containing "Cardiologist", so the app-side
specialty substring match in `geo_search` resolves the query.

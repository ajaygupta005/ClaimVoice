install:
    pnpm install
    uv sync

up:
    docker compose up -d

down:
    docker compose down

dev:
    turbo dev

test:
    pnpm test
    uv run pytest -q

lint:
    pnpm lint
    uv run ruff check .

eval:
    inspect eval eval/tasks/

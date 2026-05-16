# Convenience aliases that map to Justfile
.PHONY: install up down logs dev test eval data ingest train

install:
	just install
up:
	just up
down:
	just down
logs:
	just logs
dev:
	just dev
test:
	just test
eval:
	just eval
data:
	just data.ingest
train:
	just train.all

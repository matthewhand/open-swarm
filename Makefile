# Makefile for Open Swarm: developer/CI helpers

.PHONY: pretest-clean test

pretest-clean:
	bash scripts/pretest_cleanup.sh

test: pretest-clean
	uv run pytest

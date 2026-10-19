.DEFAULT_GOAL := help
SHELL := /bin/bash
.SHELLFLAGS := -eu -c

.PHONY: help prod-init prod prod-build prod-down prod-restart prod-logs prod-ps prod-check
help:
	$(info make prod-init     Create missing production env/config and judge key)
	$(info make prod          Start judge; build only if its image is missing)
	$(info make prod-build    Rebuild image after source changes)
	$(info make prod-down     Stop judge without changing problem data)
	$(info make prod-restart  Recreate judge to apply config)
	$(info make prod-logs     Follow judge logs)
	$(info make prod-ps       Show status)
	$(info make prod-check    Validate config and Compose)
	$(info See PRODUCTION.md for OJ registration and problem permissions.)

prod-init prod prod-build prod-down prod-restart prod-logs prod-ps prod-check:
	@bash scripts/prod.sh "$@"

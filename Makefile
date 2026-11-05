REQCOVER_REPO ?= https://github.com/reqcover/reqcover.git
REQCOVER_REF ?= trunk
REQCOVER_DIR ?= $(CURDIR)/.reqcover
REQCOVER_TREE := $(CURDIR)/.reqcover-build
REQCOVER_VERSION ?= $(shell cat .reqcover-version 2>/dev/null)
export REQCOVER_VERSION

ARGS ?=
OPEN ?= $(shell command -v xdg-open || command -v open)

GRADLE := ./gradlew --console=plain $(if $(REQCOVER_VERSION),-PreqcoverVersion=$(REQCOVER_VERSION))
PYTHON := python3 -I

.PHONY: all
## all:	Publishes ReqCover, runs every feature scenario and builds the dashboard.
all: publish-reqcover scenarios dashboard

.PHONY: publish-reqcover
## publish-reqcover:	Builds ReqCover at REQCOVER_REF (default trunk) and publishes it to ~/.m2.
publish-reqcover:
	@test -d $(REQCOVER_DIR)/.git || git clone -q $(REQCOVER_REPO) $(REQCOVER_DIR)
	git -C $(REQCOVER_DIR) fetch -q origin
	rm -rf $(REQCOVER_TREE)
	git -C $(REQCOVER_DIR) worktree prune
	git -C $(REQCOVER_DIR) worktree add -q --detach $(REQCOVER_TREE) \
		$$(git -C $(REQCOVER_DIR) rev-parse --verify -q origin/$(REQCOVER_REF) || echo $(REQCOVER_REF))
	cd $(REQCOVER_TREE) && ./gradlew --console=plain -q publishToMavenLocal
	cd $(REQCOVER_TREE) && ./gradlew --console=plain -q currentVersion \
		| sed -n 's/^Project version: //p' > $(CURDIR)/.reqcover-version
	@git -C $(REQCOVER_TREE) log --format='%h' -1 > $(CURDIR)/.reqcover-commit
	git -C $(REQCOVER_DIR) worktree remove --force $(REQCOVER_TREE)
	@echo "Published ReqCover $$(cat .reqcover-version) from $(REQCOVER_REF) at commit $$(cat .reqcover-commit)"

.PHONY: test
## test:	Runs the tests once with the default configuration; pass switches via ARGS="-PreqCoverMin=80".
test:
	$(GRADLE) test $(ARGS)

.PHONY: report
## report:	Opens the ReqCover HTML report of the last test run.
report:
	$(OPEN) build/reports/tests/reqcover/requirements-coverage.html

.PHONY: scenarios
## scenarios:	Runs every feature scenario (writes results/).
scenarios:
	$(PYTHON) scripts/run_scenarios.py

.PHONY: dashboard
## dashboard:	Builds dashboard/index.html and results/summary.md from results/.
dashboard:
	$(PYTHON) scripts/build_dashboard.py

.PHONY: open
## open:	Opens the dashboard.
open:
	$(OPEN) dashboard/index.html

.PHONY: clean
## clean:	Removes build output, results and the dashboard.
clean:
	$(GRADLE) clean
	rm -rf results dashboard

.PHONY: help
## help:	Prints this help text.
help:
	@sed -En 's/^## ?//p' $(MAKEFILE_LIST)

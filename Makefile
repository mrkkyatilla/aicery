COMPOSE := docker compose -f deploy/docker-compose.yml
PYTEST := pytest -m "not integration and not live"

.PHONY: up down logs migrate test smoke lint install unit integration gate-f1 gate-f2 gate-f3 gate-f6 gate-e7 gate-e7-p2 gate-e7-p2-live gate-gonogo gate-p95 gate-graph-steps gate-otel gate-hitl gate-hitl-chain gate-hitl-unified gate-hitl-postgres gate-providers-ext gate-providers-ext-live gate-gateway-policy gate-gateway-policy-e2e gate-demo-examples gate-v3-sdk gate-marketplace gate-router-llm gate-stock-product gate-privacy-proxy gate-context-compactor gate-drift-eval gate-trace-miner gate-sandbox gate-s4-modules build-api load-f1 load-f2 load-beta demo-e7

install:
	pip install -e ./core -e ./agents -e ./tools -e "./runtime[dev]" -e ./sdk/python -e ./cli -e "./services/gateway[dev]"

gateway-unit:
	pytest services/gateway/tests -q

billing-ui-smoke:
	bash scripts/billing_ui_smoke.sh

gateway-migrate:
	cd services/gateway && alembic upgrade head

lint:
	ruff check core runtime agents tools cli tests
	bash -n scripts/qdrant_backup.sh scripts/p95_gate.sh scripts/issue_dev_jwt.sh scripts/issue_tenant_jwt.sh scripts/graph_steps_gate.sh scripts/otel_unit_gate.sh scripts/hitl_unit_gate.sh scripts/hitl_chain_gate.sh scripts/hitl_unified_gate.sh scripts/hitl_postgres_gate.sh scripts/providers_ext_gate.sh scripts/providers_ext_live_gate.sh scripts/gateway_policy_gate.sh scripts/gateway_policy_e2e_gate.sh scripts/demo_examples_gate.sh scripts/v3_sdk_gate.sh scripts/marketplace_gate.sh scripts/router_llm_gate.sh scripts/stock_product_gate.sh scripts/privacy_proxy_gate.sh scripts/context_compactor_gate.sh scripts/drift_eval_gate.sh scripts/trace_miner_gate.sh scripts/sandbox_gate.sh \
		examples/workspace-analyst/scripts/demo.sh examples/stock-advisor/scripts/demo.sh \
		examples/runbook-agent/scripts/demo.sh examples/compliance-scan/scripts/demo.sh \
		examples/support-drafter/scripts/demo.sh examples/sales-research/scripts/demo.sh

unit:
	$(PYTEST) core/tests runtime/tests tools/tests

test: unit

integration:
	$(COMPOSE) up -d --wait postgres redis nats qdrant --remove-orphans
	$(COMPOSE) run --rm --build migrate
	MOCK_STREAM_DELAY_SEC=3 USE_MOCK_PROVIDER=true RATE_LIMIT_ENABLED=true RATE_LIMIT_BACKEND=redis RATE_LIMIT_PER_MINUTE=100 \
		$(COMPOSE) up -d --build --wait api --remove-orphans
	pytest -m "integration and not rate_limit_integration" tests/integration
	pytest -m rate_limit_integration tests/integration
	$(COMPOSE) down

gate-f2: install unit
	bash scripts/f2_exit_gate.sh

gate-f3: install unit
	bash scripts/f3_exit_gate.sh

gate-e7: install
	bash scripts/e7_exit_gate.sh

gate-e7-p2: install
	bash scripts/e7_p2_gate.sh

gate-e7-p2-live: install up
	E7_PERF_STRICT=1 bash scripts/e7_p2_live_gate.sh

# Rebuild API+Qdrant then run gate with live index check (fails if index still broken).
gate-e7-live: install up
	E7_GATE_STRICT=1 bash scripts/e7_exit_gate.sh

gate-f6: install
	DOCKER_BUILDKIT=1 bash scripts/f6_beta_gate.sh

# E6-β2 — ≥4/5 scorecard: gate-f3 + gate-e7-p2 + gate-f6 + golden + trace smoke
gate-gonogo: install
	DOCKER_BUILDKIT=1 bash scripts/go_no_go_gate.sh

gate-p95: up
	bash scripts/p95_gate.sh

gate-graph-steps: install
	bash scripts/graph_steps_gate.sh

gate-otel: install
	bash scripts/otel_unit_gate.sh

gate-hitl: install
	bash scripts/hitl_unit_gate.sh

gate-hitl-chain: install
	bash scripts/hitl_chain_gate.sh

gate-hitl-unified: install
	bash scripts/hitl_unified_gate.sh

gate-providers-ext: install
	bash scripts/providers_ext_gate.sh

gate-hitl-postgres: install
	bash scripts/hitl_postgres_gate.sh

gate-gateway-policy: install
	bash scripts/gateway_policy_gate.sh

gate-gateway-policy-e2e: install
	bash scripts/gateway_policy_e2e_gate.sh

gate-demo-examples: install
	bash scripts/demo_examples_gate.sh

gate-v3-sdk:
	bash scripts/v3_sdk_gate.sh

gate-marketplace: install
	bash scripts/marketplace_gate.sh

gate-router-llm: install
	bash scripts/router_llm_gate.sh

gate-stock-product: install
	bash scripts/stock_product_gate.sh

gate-privacy-proxy: install
	bash scripts/privacy_proxy_gate.sh

gate-context-compactor: install
	bash scripts/context_compactor_gate.sh

gate-drift-eval: install
	bash scripts/drift_eval_gate.sh

gate-trace-miner: install
	bash scripts/trace_miner_gate.sh

gate-sandbox: install
	bash scripts/sandbox_gate.sh

# Sprint 4 — tüm motor modülü + SANDBOX gate'leri (DoD matrisi)
gate-s4-modules: gate-privacy-proxy gate-context-compactor gate-drift-eval gate-trace-miner gate-sandbox

gate-providers-ext-live: install
	bash scripts/providers_ext_live_gate.sh

# Force API image rebuild (e.g. after code change); set F6_FORCE_BUILD=1 for gate-f6 too.
build-api:
	DOCKER_BUILDKIT=1 $(COMPOSE) build api

demo-e7:
	bash examples/research-docs/run_e7.sh

load-beta:
	$(COMPOSE) up -d --wait postgres redis nats qdrant --remove-orphans
	$(COMPOSE) run --rm --build migrate
	DOCKER_BUILDKIT=1 RATE_LIMIT_ENABLED=false USE_MOCK_PROVIDER=true \
		$(COMPOSE) up -d --build --wait api --remove-orphans
	pytest tests/load/test_concurrent_beta_50.py -m load -q

gate-f1: up
	pytest tests/integration/weekly_gate.py tests/integration/test_f1_exit_gate.py -m integration -q
	bash scripts/f1_exit_gate.sh

load-f1: up
	pytest tests/load/test_concurrent_runs_f1.py -m load -q

load-f2: up
	pytest tests/load -m load -q

# Requires: export GEMINI_API_KEY=... USE_MOCK_PROVIDER=false
PYTEST ?= .venv/bin/pytest

live:
	pytest runtime/tests/live -m live -q

live-api:
	@test -n "$$GEMINI_API_KEY" || (echo "Set GEMINI_API_KEY in shell (do not commit .env)" && exit 1)
	$(COMPOSE) up -d --wait postgres redis nats qdrant --remove-orphans
	$(COMPOSE) run --rm --build migrate
	USE_MOCK_PROVIDER=false GEMINI_MODEL=$${GEMINI_MODEL:-gemini-2.5-flash} \
		$(COMPOSE) up -d --build --wait api --remove-orphans
	pytest runtime/tests/live/test_echo_live_api.py runtime/tests/live/test_research_live_api.py -m live -q

live-research:
	@test -n "$$GEMINI_API_KEY" || (echo "Set GEMINI_API_KEY in shell (do not commit .env)" && exit 1)
	pytest runtime/tests/live/test_gemini_live.py runtime/tests/live/test_research_live.py -m live -q

up:
	$(COMPOSE) up -d --wait postgres redis nats qdrant --remove-orphans
	$(COMPOSE) run --rm --build migrate
	$(COMPOSE) up -d --build --wait api --remove-orphans

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) run --rm --build migrate

smoke:
	curl -sf http://localhost:8000/health | grep -q '"status":"ok"'

logs:
	$(COMPOSE) logs -f api

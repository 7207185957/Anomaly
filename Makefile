.PHONY: backend-run backend-worker frontend-dev compose-up compose-down

backend-run:
	cd apps/backend && uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload

backend-worker:
	cd apps/backend && rq worker rca-jobs

frontend-dev:
	cd apps/frontend && npm run dev

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v

cloud-bootstrap:
	./scripts/cloud-agent-bootstrap.sh

cloud-verify:
	./scripts/cloud-agent-verify.sh


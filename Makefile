.PHONY: up down logs demo investigate test
up:
	docker compose up --build -d
down:
	docker compose down -v
logs:
	docker compose logs -f
demo:
	powershell -ExecutionPolicy Bypass -File .\faults\run-demo.ps1
investigate:
	curl -X POST http://localhost:8081/api/investigations -H "Content-Type: application/json" -d "{\"question\":\"Why is checkout failing?\"}"
test:
	pytest -q

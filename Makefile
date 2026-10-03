.PHONY: install check backend frontend

install:
	cd backend && python3 -m pip install -e '.[dev]'
	cd frontend && npm install

check:
	python3 validate_examples.py
	cd backend && python3 -m pytest -q
	cd frontend && npx tsc --noEmit

backend:
	cd backend && uvicorn labforge.gateway:app --reload --port 8000

frontend:
	cd frontend && npx vite

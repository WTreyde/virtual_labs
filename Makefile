.PHONY: install check backend frontend demo

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

# One command, one URL: build the game and serve it with the API on http://localhost:8000
demo:
	cd frontend && VITE_API= npx vite build
	cd backend && uvicorn labforge.gateway:app --port 8000

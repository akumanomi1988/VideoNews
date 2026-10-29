.PHONY: install clean lint typecheck test run run-dashboard

VENV = .venv
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip

install: $(VENV)
	$(PIP) install -e ".[dev]"

$(VENV):
	python -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel

clean:
	rm -rf $(VENV)
	rm -rf *.egg-info
	rm -rf __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

lint:
	$(VENV)/Scripts/ruff check .

typecheck:
	$(VENV)/Scripts/mypy scripts/ news_video_processor.py

test:
	$(VENV)/Scripts/pytest -v

run:
	$(PYTHON) -m scripts.cli --help

run-dashboard:
	$(PYTHON) scripts/run_dashboard.py

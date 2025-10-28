# Selenium Python Starter (Pytest + Page Objects)

A production-ready starter kit for UI automation with **Selenium 4**, **Pytest**, and **Page Object Model (POM)**.

## Quick start

```bash
# 1) Create & activate a virtualenv (recommended)
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure (optional)
cp .env.example .env
# edit .env as needed (BROWSER, HEADLESS, BASE_URL, etc.)

# 4) Run tests
pytest -q
# or with html report
pytest --html=reports/report.html --self-contained-html
```

> **Note**: Selenium 4 uses **Selenium Manager** to auto-install drivers for you; no extra setup is needed on most systems.

## Useful CLI overrides

```bash
pytest -q --browser firefox --headless true --base-url https://www.python.org
pytest -q -m smoke
```

## Project structure

```
selenium-python-starter/
  .env.example
  pytest.ini
  requirements.txt
  src/
    core/                # shared infra: config, driver, logging, base page
    pages/               # Page Objects
    tests/               # pytest tests + fixtures
```

## Extending
- Put new pages under `src/pages/*_page.py` (one class per page).
- Reuse waits in `BasePage` or add custom ones to `core/wait.py`.
- Add markers (`@pytest.mark.smoke`) to group suites.
- Screenshots on failure saved in `artifacts/screenshots`.

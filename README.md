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
    orchestrator.py      # Service entrypoint wiring the Selenium flows
```

## Extending
- Put new pages under `src/pages/*_page.py` (one class per page).
- Reuse waits in `BasePage` or add custom ones to `core/wait.py`.
- Add markers (`@pytest.mark.smoke`) to group suites.
- Screenshots on failure saved in `artifacts/screenshots`.

## Automation orchestrator

The orchestrator lives in `src/orchestrator.py` and exposes a `handler(event)` function that selects the appropriate Selenium flow and returns uploaded file metadata. The FastAPI service routes POST `/api/run` requests directly to this handler so the same payload structure can be reused across deployment targets.

### Invocation payload

```json
{
  "site": "zio",                     // xr | quest | zio | tricore
  "credentials": {
    "username": "...",
    "password": "..."
  },                                // optional when credentials come from Secrets Manager
  "patient": {
    "first_name": "Jane",
    "last_name": "Doe",
    "dob": "01011980"               // optional for Zio/XR, required for Quest/Tricore
  },
  "options": {
    "start_date": "01012023",        // optional, used by XR
    "end_date": "02012023",          // optional, used by XR
    "gender": "F"                    // required for Tricore only
  }
}
```

The service response includes the resolved site plus a `patient_files` array describing each uploaded report and its access URLs.

### S3 uploads

Set the following environment variables to mirror downloads in Amazon S3:

```
DOWNLOAD_S3_BUCKET=runner-downloads-bucket
DOWNLOAD_S3_PREFIX=selenium-downloads
DOWNLOAD_S3_PREFIX_ZIO=ziosuite
DOWNLOAD_S3_PREFIX_XR=xraynm
DOWNLOAD_S3_PREFIX_QUEST=quest
DOWNLOAD_S3_PREFIX_TRICORE=tricore
DOWNLOAD_S3_REGION=eu-north-1
DOWNLOAD_S3_URL_EXPIRATION=No Expiry  # integer seconds for presigned URLs; "No Expiry" defaults to 7 days
DOWNLOAD_S3_DIRECT=false             # true deletes local copies after uploading
ZIO_SECRET_ARN=arn:aws:secretsmanager:...:secret:selenium/zio
XR_SECRET_ARN=arn:aws:secretsmanager:...:secret:selenium/xr
QUEST_SECRET_ARN=arn:aws:secretsmanager:...:secret:selenium/quest
TRICORE_SECRET_ARN=arn:aws:secretsmanager:...:secret:selenium/tricore
```

When set, each automation run uploads its downloaded files to `s3://DOWNLOAD_S3_BUCKET/DOWNLOAD_S3_PREFIX/<site>/<timestamp>/...`. Each object receives a presigned HTTPS URL (default 7-day expiry when `DOWNLOAD_S3_URL_EXPIRATION` is omitted or "No Expiry"). Enabling `DOWNLOAD_S3_DIRECT=true` removes the local PDFs after a successful upload so that S3 becomes the system of record.

### Container build

Build the container image and push it to Amazon ECR for ECS deployment:

```bash
docker build -t selenium-automation-service .
# tag & push to <account>.dkr.ecr.<region>.amazonaws.com/selenium-automation-service
```

Provision an ECS service (Fargate or EC2) with the pushed image, supply the required environment variables (or Secrets Manager references), and expose port 8080 for the FastAPI endpoint. For local testing, run `uvicorn src.api.app:app --host 0.0.0.0 --port 8080` and send requests to `http://localhost:8080/api/run`. The backend exposes both `/api/run` and `/run` for compatibility with independently hosted frontends.

### Frontend container

The React UI lives under `ui/` and can be built into a standalone container using `Dockerfile.frontend`. Set `VITE_API_BASE_URL` at build time so the compiled assets know which backend to call:

```bash
docker buildx build --platform linux/amd64 \
  --build-arg VITE_API_BASE_URL=http://your-backend-host:8080 \
  -t selenium-automation-ui \
  -f Dockerfile.frontend .
```

Deploy the resulting image behind a simple load balancer or static hosting service. The frontend always posts to `<VITE_API_BASE_URL>/run`.

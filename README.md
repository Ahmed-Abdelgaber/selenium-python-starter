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
    lambda_handler.py    # AWS Lambda entrypoint wiring the Selenium flows
```

## Extending
- Put new pages under `src/pages/*_page.py` (one class per page).
- Reuse waits in `BasePage` or add custom ones to `core/wait.py`.
- Add markers (`@pytest.mark.smoke`) to group suites.
- Screenshots on failure saved in `artifacts/screenshots`.

## Lambda automation handler

Deploy the project as an AWS Lambda container image. The entry point `src/lambda_handler.py` exposes a `handler(event, context)` function that selects the appropriate Selenium flow and returns uploaded file metadata.

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

The Lambda response includes the resolved site plus a `patient_files` array describing each uploaded report and its presigned URL.

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

When set, each Lambda invocation uploads its downloaded files to `s3://DOWNLOAD_S3_BUCKET/DOWNLOAD_S3_PREFIX/<site>/<timestamp>/...`. Each object receives a presigned HTTPS URL (default 7-day expiry when `DOWNLOAD_S3_URL_EXPIRATION` is omitted or "No Expiry"). Enabling `DOWNLOAD_S3_DIRECT=true` removes the local PDFs after a successful upload so that S3 becomes the system of record.

### Container build

Build the Lambda-ready container image and push it to Amazon ECR:

```bash
docker build -t selenium-automation-lambda .
# tag & push to <account>.dkr.ecr.<region>.amazonaws.com/selenium-automation-lambda
```

Create a Lambda function that points at that image, supply the required environment variables (or Secrets Manager references), and invoke the function either directly via the AWS SDK or through API Gateway. For local testing, use AWS SAM CLI or the Lambda Runtime Interface Emulator to replay events against the image.

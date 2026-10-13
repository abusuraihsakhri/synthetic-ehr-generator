# Synthetic EHR Generator

A small, reproducible fixture generator for testing healthcare software. It produces **artificial** Patient, Encounter, Observation and optional Condition resources in a FHIR R4-shaped collection bundle, or a flat CSV table. It also retains the repository's separate example task-evaluation CLI and FastAPI service.

The generated data are **not clinically validated**, drawn from real patient records, privacy-certified, or guaranteed to satisfy every FHIR profile. Do not use this software for clinical decisions or enter real patient information.

## Browser application

The [browser interface](web/index.html) generates records and downloads JSON/CSV entirely on-device. There are no third-party JavaScript libraries, external fonts, network requests or uploads. Enter a patient count from 1 to 1000 and optionally a random seed; generate a preview, then download either format.

For local development, serve the static files over HTTP (module scripts may be blocked when opened through a `file://` URL):

```bash
python -m http.server 8080 --directory web
# Visit http://localhost:8080
```

GitHub Pages deployment is defined in `.github/workflows/pages.yml`; the repository owner must enable **Settings → Pages → Build and deployment → GitHub Actions**. A public live URL will be added when deployment is verified.

## Python usage

Python 3.10 or later is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# Generate 20 synthetic patients in a FHIR-shaped JSON bundle:
python cli.py generate --count 20 --seed 42 --format json --output generated/fixtures.json

# Generate a CSV table:
python cli.py generate --count 20 --seed 42 --format csv --output generated/fixtures.csv

# Equivalent generation via the standalone module:
python synthetic_ehr.py generate --count 10 --seed 42 --output generated/bundle.json
```

The Python and JavaScript implementations each reproduce output with the same seed **within their own implementation**; they do not produce byte-identical records across languages.

### Existing demonstration workflows

```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
python cli.py chat "Explain evaluation criteria"
python cli.py batch -i input.csv -o results.csv
python cli.py verify-audit

# Legacy generic keyword/CSV lookup, independent of EHR generation:
python synthetic_ehr.py single creatinine
python synthetic_ehr.py batch --input sample.csv --output generated/lookups.csv
```

The three evaluation workers use illustrative, fixed thresholds (primary metric >25, secondary metric >12, critical flag, and status keywords). These are **not disease-specific clinical thresholds or standards-conformance checks**. The chat interface is a deterministic mock, not a live external LLM.

## FastAPI service

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python cli.py serve --host 127.0.0.1 --port 8000

curl 'http://127.0.0.1:8000/health'
curl 'http://127.0.0.1:8000/api/generate?count=5&seed=42'
curl -X POST 'http://127.0.0.1:8000/api/audit' \
  -H 'Content-Type: application/json' \
  -d '{"task_id":"T1","target_identifier":"SYN-001","primary_metric":12.0}'
```

Other endpoints: `POST /api/chat`, `GET /api/audit/logs`, `GET /metrics` (JSON counters), and generated FastAPI documentation at `/docs`.

For container deployment, set `AUDIT_SECRET_KEY` to a random secret before running `docker compose up --build`. The API has **no authentication or rate limiting**; do not expose it to the public internet without appropriate controls.

## Security and privacy limitations

- The browser generator operates entirely locally and uses fabricated IDs, dates, diagnosis labels and laboratory values. It does **not** process supplied patient records.
- The Python evaluation engine has a **heuristic regex guard** for several identifying patterns. It is **not a de-identification solution** and cannot guarantee the absence of protected health information.
- Task audits use HMAC-SHA256 over canonical metadata with a verified hash chain. The audit key must be configured for persistent key identity. The audit log itself is held **in process memory**, not durable storage.
- No remote-model integration is implemented. The only supported model provider is the local deterministic mock.
- Synthetic distributions, associations, codes and units are demonstration fixtures, not validated research cohorts.

## Tests

```bash
python -m pytest -q
python -m compileall -q agents ehr_generation.py synthetic_ehr.py cli.py
node --check web/app.mjs
node --test tests/test_browser.mjs
```

CI runs Python tests on 3.10, 3.11 and 3.12, along with static browser checks. Node.js 22 or later is recommended for the local browser test suite; it is not needed to use the browser app.

## Technology and compatibility

Python standard library for fixture generation, Pydantic 2 / FastAPI / Uvicorn for the optional API, HTML/CSS/ES modules for the offline browser app, pytest and Node's built-in test runner for verification. Recent versions of Chrome, Firefox, Safari and Edge support the required browser APIs; cross-browser manual testing has not been certified.

## License

[MIT](LICENSE).

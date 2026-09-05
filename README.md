# Synthetic EHR Generator

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Standards:** CAP / CLSI / ISO Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

Synthetic EHR Generator produces synthetic FHIR-like EHR encounters with demographics, labs, and ICD codes for safe testing environments. It includes a multi-worker evaluation engine with PHI outbound protection and cryptographic audit trails.

---

## Key Features

- **Zero-PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers from leaving the system.
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation with tamper detection.
- **Multi-Worker Evaluation:** Three specialized workers (QC Invariant, Safety Escalation, Protocol Conformance) analyze each task.
- **FastAPI REST API:** OpenAPI 3.1 endpoints with Prometheus metrics.
- **Batch CSV Processing:** Process large datasets with automatic column detection.
- **CLI Interface:** Full command-line interface for all operations.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/synthetic-ehr-generator.git
cd synthetic-ehr-generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install fastapi uvicorn pydantic pytest
```

---

## Configuration

Set the audit secret key for production (optional for development):

```bash
export AUDIT_SECRET_KEY="your-secure-random-key-here"
```

If not set, an ephemeral development key is generated with a warning.

---

## Usage

### CLI Commands

```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Chat with supervisor
python cli.py chat "Explain the evaluation criteria"

# Batch process CSV
python cli.py batch -i input.csv -o results.csv

# Verify audit trail integrity
python cli.py verify-audit

# Start API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Direct Module Usage

```python
import synthetic_ehr as sehr

# Single lookup
result = sehr.lookup("creatinine")
print(result["top_hit"], result["score"])

# Batch CSV processing
rows = sehr.process_csv("input.csv", "output.csv")
print(f"Processed {len(rows)} rows")
```

### API Server

```bash
# Start server
python cli.py serve

# Health check
curl http://localhost:8000/health

# Submit task
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"task-id":"T001","target-identifier":"KEY-01","primary_metric":12.0}'

# Get audit logs
curl http://localhost:8000/api/audit/logs
```

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=agents --cov=synthetic_ehr

# Run simulation benchmark
python simulator.py 100
```

---

## Project Structure

```
synthetic-ehr-generator/
├── agents/                  # Core evaluation engine
│   ├── __init__.py
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # PHI Guard, Audit Trail, Security
│   ├── learning.py         # Bayesian calibration engine
│   ├── llm_factory.py      # LLM provider abstraction
│   ├── metrics.py          # Prometheus metrics collector
│   ├── models.py           # Pydantic data models
│   ├── streamer.py         # WebSocket telemetry
│   ├── supervisor.py       # Multi-worker orchestrator
│   └── workers.py          # Specialized evaluation workers
├── tests/                   # Test suite
│   ├── test_enrichment.py
│   ├── test_security_and_validation.py
│   └── test_synthetic_ehr_generator.py
├── cli.py                   # Command-line interface
├── simulator.py             # High-throughput stress testing
├── enrichment.py            # Feature enrichment engines
├── synthetic_ehr.py         # Core EHR generation & lookup
├── web/                     # Static web assets
├── Dockerfile               # Container build
├── docker-compose.yml       # Container orchestration
├── openapi_spec.json        # OpenAPI specification
└── benchmark_dataset.json   # Golden benchmark test cases
```

---

## Security

- **PHI Protection:** All outbound data is scanned for PHI patterns before leaving the system.
- **Audit Integrity:** HMAC-SHA256 chained audit logs detect any tampering.
- **No Hardcoded Secrets:** Audit keys use environment variables or ephemeral generation.
- **Input Validation:** All file inputs are validated for existence and format.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

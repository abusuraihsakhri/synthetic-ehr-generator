"""Regression coverage for real synthetic fixture generation and input safety."""
import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ehr_generation import CSV_FIELDS, generate_bundle, generate_records, write_csv
from agents.api import ChatRequest, api_audit, api_chat
from agents.base import AuditTrail, SecurityException
from agents.models import SystemTaskPayload
from cli import main as cli_main


def test_reproducible_records_and_unique_ids():
    rows = generate_records(50, seed=21)
    assert rows == generate_records(50, seed=21)
    assert rows != generate_records(50, seed=22)
    assert len(set(row["patient_id"] for row in rows)) == 50
    assert all(0.5 <= row["creatinine_mg_dl"] <= 1.8 for row in rows)


@pytest.mark.parametrize("count", [0, -1, 1001, True, 1.5, "10"])
def test_reject_invalid_counts(count):
    with pytest.raises(ValueError):
        generate_records(count)


def test_bundle_references_and_structure():
    bundle = generate_bundle(25, 123)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert sum(e["resource"]["resourceType"] == "Patient" for e in bundle["entry"]) == 25
    assert sum(e["resource"]["resourceType"] == "Encounter" for e in bundle["entry"]) == 25
    assert sum(e["resource"]["resourceType"] == "Observation" for e in bundle["entry"]) == 25
    identifiers = {e["resource"]["resourceType"] + "/" + e["resource"]["id"] for e in bundle["entry"]}
    for entry in bundle["entry"]:
        assert entry["fullUrl"].startswith("https://example.invalid/fhir/")
        for ref_name in ("subject", "encounter"):
            ref = entry["resource"].get(ref_name)
            if ref:
                assert ref["reference"] in identifiers


def test_csv_and_both_command_line_interfaces(tmp_path):
    csv_out = tmp_path / "sub" / "data.csv"
    json_out = tmp_path / "other" / "data.json"
    write_csv(generate_records(3, seed=1), csv_out)
    with csv_out.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3
    assert set(CSV_FIELDS) == set(rows[0])
    assert cli_main(["generate", "--count", "3", "--seed", "1", "--output", str(json_out)]) == 0
    assert len(json.loads(json_out.read_text())["entry"]) >= 9
    assert cli_main(["generate", "--count", "0", "--output", str(csv_out), "--format", "csv"]) == 1
    from synthetic_ehr import main as module_main
    assert module_main(["generate", "--count", "2", "--seed", "3", "--output", str(json_out)]) == 0


def test_hmac_verifies_metadata_not_just_chain_link():
    trail = AuditTrail(secret_key="unit-test-key")
    trail.log("actor", "unit", "EVENT", {"value": 1})
    trail.log("actor", "unit", "EVENT", {"value": 2})
    assert trail.verify_integrity()
    copy = trail.get_trail()
    copy[0]["payload_hash"] = "wrong"
    assert trail.verify_integrity(), "Public trail snapshots must not mutate internal entries"
    trail.logs[1]["payload_hash"] = "changed"
    assert trail.verify_integrity() is False


def test_invalid_metrics_rejected():
    with pytest.raises(ValidationError):
        SystemTaskPayload(task_id="t", target_identifier="k", primary_metric=float("nan"))
    with pytest.raises(ValidationError):
        SystemTaskPayload(task_id="t", target_identifier="k", primary_metric=float("inf"))


def test_api_rejects_sensitive_values_and_nested_metadata():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        api_audit(SystemTaskPayload(
            task_id="t", target_identifier="MRN-123456", primary_metric=4,
        ))
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        api_chat(ChatRequest(query="john@example.com"))
    assert exc.value.status_code == 400
    with pytest.raises(SecurityException):
        from agents.supervisor import SystemSupervisor
        SystemSupervisor().process_task(SystemTaskPayload(
            task_id="t", target_identifier="key", primary_metric=1,
            attributes={"contact": "person@example.com"},
        ))


def test_api_generate_returns_linked_bundle():
    from agents.api import api_generate
    result = api_generate(count=4, seed=123)
    assert result["resourceType"] == "Bundle"
    assert sum(item["resource"]["resourceType"] == "Patient" for item in result["entry"]) == 4

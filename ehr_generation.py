"""Deterministic, entirely synthetic EHR fixtures for software testing.

FHIR R4-shaped Patient, Encounter, Condition and Observation resources are
intentionally small examples, not clinically validated records or a conformant
implementation of an EHR / FHIR server.
"""
import csv
import random
import secrets
from datetime import date, timedelta
from pathlib import Path

CONDITIONS = (
    ("I10", "Essential (primary) hypertension"),
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("J45.909", "Unspecified asthma, uncomplicated"),
    ("", ""),
)
CSV_FIELDS = (
    "patient_id", "encounter_id", "gender", "birth_date", "encounter_date",
    "condition_code", "condition_display", "creatinine_mg_dl",
)


def generate_records(count: int = 10, seed: int | None = None) -> list[dict]:
    """Create 1–1000 reproducible synthetic rows (seed=None randomizes each run)."""
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000:
        raise ValueError("count must be an integer between 1 and 1000")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or None")
    rng = random.Random(seed if seed is not None else secrets.randbits(64))
    records = []
    for i in range(1, count + 1):
        years_old = rng.randrange(18, 91)
        birth_date = date(2025 - years_old, rng.randint(1, 12), rng.randint(1, 28))
        encounter_date = date(2025, 1, 1) + timedelta(days=rng.randrange(365))
        code, label = rng.choice(CONDITIONS)
        records.append({
            "patient_id": f"SYN-P{i:05d}",
            "encounter_id": f"SYN-E{i:05d}",
            "gender": rng.choice(("female", "male", "unknown")),
            "birth_date": birth_date.isoformat(),
            "encounter_date": encounter_date.isoformat(),
            "condition_code": code,
            "condition_display": label,
            "creatinine_mg_dl": round(rng.uniform(0.5, 1.8), 2),
        })
    return records


def generate_bundle(count: int = 10, seed: int | None = None) -> dict:
    """Generate a FHIR R4-shaped collection bundle with internally linked resources."""
    entries = []
    for row in generate_records(count=count, seed=seed):
        pid = row["patient_id"]
        eid = row["encounter_id"]
        resources = [
            {
                "resourceType": "Patient", "id": pid,
                "identifier": [{"system": "https://example.invalid/synthetic-patient",
                                "value": pid}],
                "gender": row["gender"], "birthDate": row["birth_date"],
            },
            {
                "resourceType": "Encounter", "id": eid, "status": "finished",
                "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                          "code": "AMB"},
                "subject": {"reference": f"Patient/{pid}"},
                "period": {"start": f'{row["encounter_date"]}T09:00:00Z'},
            },
            {
                "resourceType": "Observation", "id": f"OBS-{pid}",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org",
                                    "code": "2160-0", "display": "Creatinine"}]},
                "subject": {"reference": f"Patient/{pid}"},
                "encounter": {"reference": f"Encounter/{eid}"},
                "effectiveDateTime": f'{row["encounter_date"]}T09:00:00Z',
                "valueQuantity": {"value": row["creatinine_mg_dl"],
                                  "unit": "mg/dL", "system": "http://unitsofmeasure.org",
                                  "code": "mg/dL"},
            },
        ]
        if row["condition_code"]:
            resources.append({
                "resourceType": "Condition", "id": f"COND-{pid}",
                "clinicalStatus": {"coding": [{"system":
                    "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"}]},
                "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm",
                                    "code": row["condition_code"],
                                    "display": row["condition_display"]}]},
                "subject": {"reference": f"Patient/{pid}"},
                "encounter": {"reference": f"Encounter/{eid}"},
            })
        entries.extend({"fullUrl": f'urn:uuid:{r["resourceType"]}-{r["id"]}', "resource": r}
                       for r in resources)
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def write_csv(records: list[dict], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

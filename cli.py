"""
Command Line Interface for Synthetic Ehr Generator.
"""
import argparse
import csv
import json
import sys
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from agents.base import AuditLogger
from ehr_generation import generate_bundle, generate_records, write_csv

supervisor = SystemSupervisor(model_provider="mock")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="synthetic-ehr-generator", description="Synthetic Ehr Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Verify Audit
    subparsers.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    # Synthetic test fixtures
    p_generate = subparsers.add_parser("generate", help="Generate synthetic EHR records")
    p_generate.add_argument("--count", type=int, default=10)
    p_generate.add_argument("--seed", type=int, default=None)
    p_generate.add_argument("--format", choices=("json", "csv"), default="json")
    p_generate.add_argument("-o", "--output", required=True)

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print("=" * 80)
        print(f"  SYNTHETIC EHR GENERATOR")
        print(f"  Domain: Clinical & Biomedical AI | Standard: CAP / CLSI / ISO Standards")
        print(f"  Dossier ID: {dossier.dossier_id} | Urgency: [{dossier.overall_urgency.value}]")
        print("=" * 80)
        for a in dossier.alerts:
            print(f"\n  [{a.urgency.value}] from {a.origin_worker}:")
            print(f"  Summary: {a.summary}")
            print(f"  Details: {a.technical_details}")
            print(f"  Action:  {a.actionable_remediation}")
        print(f"\n  HMAC-SHA256 Audit Hash: {dossier.audit_hash}")
        print("=" * 80)
        return 0

    if args.command == "chat":
        ans = supervisor.query_supervisory_chat(" ".join(args.query))
        print(f"\n[Synthetic Ehr Generator Supervisor]:\n{ans}\n")
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit Trail Blocks: {len(trail)} | Cryptographic Integrity Verified: {valid}")
        return 0

    if args.command == "batch":
        import pathlib
        inp_path = pathlib.Path(args.input)
        if not inp_path.exists():
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            return 1
        if not inp_path.is_file():
            print(f"Error: Input path is not a file: {args.input}", file=sys.stderr)
            return 1

        try:
            with open(args.input, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                if not fieldnames:
                    print(f"Error: CSV file has no headers: {args.input}", file=sys.stderr)
                    return 1
                rows = list(reader)
        except (csv.Error, UnicodeDecodeError) as e:
            print(f"Error reading CSV file: {e}", file=sys.stderr)
            return 1

        out_fields = fieldnames + ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]
        out_rows = []
        for r in rows:
            try:
                payload = SystemTaskPayload(
                    task_id=r.get("task_id", "TASK-01"),
                    target_identifier=r.get("target_identifier", "TARGET-01"),
                    primary_metric=float(r.get("primary_metric", 15.0)),
                    secondary_metric=float(r.get("secondary_metric", 5.0)),
                    status_descriptor=r.get("status_descriptor", "NOMINAL"),
                    is_critical_flag=str(r.get("is_critical_flag", "")).lower() in ("true", "1", "yes"),
                )
            except (ValueError, TypeError) as e:
                print(f"Error parsing row {r}: {e}", file=sys.stderr)
                continue
            dossier = supervisor.process_task(payload)
            row_dict = dict(r)
            row_dict["overall_urgency"] = dossier.overall_urgency.value
            row_dict["integrity_status"] = dossier.integrity_status.value
            row_dict["total_alerts"] = dossier.total_alerts
            row_dict["audit_hash"] = dossier.audit_hash
            out_rows.append(row_dict)

        try:
            out_dir = pathlib.Path(args.output).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(args.output, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
        except (IOError, OSError) as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            return 1
        print(f"Processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "generate":
        from pathlib import Path
        try:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if args.format == "csv":
                write_csv(generate_records(args.count, args.seed), destination)
            else:
                destination.write_text(
                    json.dumps(generate_bundle(args.count, args.seed), indent=2) + "\n",
                    encoding="utf-8",
                )
        except (ValueError, OSError) as exc:
            print(f"Generation failed: {exc}", file=sys.stderr)
            return 1
        print(f"Generated {args.count} synthetic records -> {args.output}")
        return 0

    if args.command == "serve":
        import uvicorn
        from agents.api import app
        print(f"Starting Synthetic Ehr Generator API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

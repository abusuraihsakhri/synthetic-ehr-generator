#!/usr/bin/env python3
"""
Synthetic EHR Generator
Generates synthetic FHIR-like EHR encounters with demographics, labs and ICD codes for testing.
Stdlib parser / mapper with batch CSV and single lookup.
"""
import argparse, csv, sys, re, json, pathlib
from ehr_generation import generate_records, generate_bundle, write_csv

def lookup(query, extra=None):
    """Single lookup: token overlap + substring scoring (no deps). Returns top hits."""
    q = str(query).lower().strip()
    # tiny built-in dictionary per project slug for demo
    bank = {
        "loinc-lab-mapper": [("2160-0 Creatinine","creatinine"),("6690-2 WBC","wbc"),("718-7 Hemoglobin","hemoglobin"),("4548-4 HbA1c","hba1c")],
        "hla-compatibility-matcher": [("A*02:01","A02"),("B*07:02","B07"),("DRB1*15:01","DRB115")],
        "icd10-ccsr-mapper": [("I10 Hypertension","I10"),("E11 Type 2 diabetes","E11"),("J18 Pneumonia","J18")],
        "antibiogram-mdr-classifier": [("MDR","multidrug"),("XDR","extensive"),("PDR","pandrug")],
        "fhir-bundle-validator": [("Patient","patient"),("Observation","observation")],
        "cyp-drug-interaction-checker": [("CYP3A4 substrate","cyp3a4"),("CYP2D6 inhibitor","cyp2d6")],
    }
    candidates = bank.get("synthetic-ehr-generator", [("generic hit","generic")])
    scored=[]
    for label,key in candidates:
        score = 0
        if key in q: score+=10
        # token overlap
        qt=set(q.split()); lt=set(label.lower().split())
        overlap=len(qt & lt)
        score+=overlap*2
        scored.append((score,label))
    scored.sort(reverse=True)
    top=scored[0] if scored else (0,"no match")
    return {"query": query, "top_hit": top[1], "score": top[0], "all": scored[:3]}

def process_csv(inp,out):
    import csv
    inp_path = pathlib.Path(inp)
    out_path = pathlib.Path(out)
    if not inp_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {inp}")
    if not inp_path.is_file():
        raise ValueError(f"Input path is not a file: {inp}")
    with open(inp, newline="", encoding="utf-8-sig") as f:
        r=csv.DictReader(f); rows=list(r); fn=r.fieldnames
        if not fn:
            raise ValueError(f"CSV file has no headers: {inp}")
        # guess query column
        qcol = fn[0]
        for cand in ["query","test","drug","code","variant","hla","lab","name"]:
            if cand in [c.lower() for c in fn]:
                qcol = [c for c in fn if c.lower()==cand][0]; break
        results=[]
        for row in rows:
            res=lookup(row.get(qcol,""), row)
            merged={**row, "top_hit": res["top_hit"], "lookup_score": res["score"]}
            results.append(merged)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(fn)+["top_hit","lookup_score"]); w.writeheader(); w.writerows(results)
    return results

def build_parser():
    p=argparse.ArgumentParser(prog="synthetic_ehr", description="Synthetic EHR Generator")
    sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("single"); s.add_argument("query", nargs="?", default="creatinine"); s.add_argument("--query", dest="q2")
    b=sub.add_parser("batch"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    g=sub.add_parser("generate", help="Create synthetic EHR fixtures")
    g.add_argument("--count", type=int, default=10)
    g.add_argument("--seed", type=int)
    g.add_argument("--format", choices=("json", "csv"), default="json")
    g.add_argument("--output", required=True)
    return p

def main(argv=None):
    p=build_parser(); a=p.parse_args(argv)
    if a.cmd=="single":
        q=getattr(a,"q2",None) or getattr(a,"query")
        print(lookup(q)); return 0
    if a.cmd=="batch":
        res=process_csv(a.input, a.output); print(f"Processed {len(res)} -> {a.output}"); return 0
    if a.cmd=="generate":
        try:
            if a.format == "csv":
                write_csv(generate_records(a.count, a.seed), a.output)
            else:
                path = pathlib.Path(a.output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(generate_bundle(a.count, a.seed), indent=2) + "\n", encoding="utf-8")
        except (ValueError, OSError) as exc:
            print(f"Generation failed: {exc}", file=sys.stderr)
            return 1
        print(f"Generated {a.count} synthetic records -> {a.output}")
        return 0
    p.print_help(); return 1

if __name__=="__main__":
    import sys; sys.exit(main())

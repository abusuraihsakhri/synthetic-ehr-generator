/* Local-only EHR test fixtures. No network calls, dependencies or PHI collection. */
const CONDITIONS = [
  ["I10", "Essential (primary) hypertension"],
  ["E11.9", "Type 2 diabetes mellitus without complications"],
  ["J45.909", "Unspecified asthma, uncomplicated"],
  ["", ""],
];
const COLUMNS = ["patient_id", "encounter_id", "gender", "birth_date", "encounter_date", "condition_code", "condition_display", "creatinine_mg_dl"];

export function parseCount(value) {
  const n = Number(value);
  if (!Number.isInteger(n) || n < 1 || n > 1000 || String(value).trim() === "") {
    throw new Error("Record count must be an integer from 1 through 1000.");
  }
  return n;
}

function generator(seed) {
  let state = (seed >>> 0);
  return () => {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function dateOnly(year, month, day) {
  return new Date(Date.UTC(year, month, day)).toISOString().slice(0, 10);
}
function id(prefix, index) {
  return prefix + String(index).padStart(5, "0");
}

export function generateRows(count = 10, seed = 12345) {
  count = parseCount(count);
  if (!Number.isSafeInteger(seed) || seed < 0 || seed > 4294967295) {
    throw new Error("Seed must be an integer between 0 and 4294967295.");
  }
  const rand = generator(seed);
  const rows = [];
  for (let i = 1; i <= count; i++) {
    const age = 18 + Math.floor(rand() * 73);
    const month = Math.floor(rand() * 12);
    const day = 1 + Math.floor(rand() * 28);
    const encounterOffset = Math.floor(rand() * 365);
    const code = CONDITIONS[Math.floor(rand() * CONDITIONS.length)];
    const gender = ["female", "male", "unknown"][Math.floor(rand() * 3)];
    const encounter = new Date(Date.UTC(2025, 0, 1 + encounterOffset)).toISOString().slice(0, 10);
    rows.push({
      patient_id: id("SYN-P", i),
      encounter_id: id("SYN-E", i),
      gender,
      birth_date: dateOnly(2025 - age, month, day),
      encounter_date: encounter,
      condition_code: code[0],
      condition_display: code[1],
      creatinine_mg_dl: Math.round((0.5 + rand() * 1.3) * 100) / 100,
    });
  }
  return rows;
}

export function makeBundle(rows) {
  const entries = [];
  for (const row of rows) {
    const pid = row.patient_id, eid = row.encounter_id;
    const resources = [
      {resourceType: "Patient", id: pid,
       identifier: [{system: "https://example.invalid/synthetic-patient", value: pid}],
       gender: row.gender, birthDate: row.birth_date},
      {resourceType: "Encounter", id: eid, status: "finished",
       class: {system: "http://terminology.hl7.org/CodeSystem/v3-ActCode", code: "AMB"},
       subject: {reference: "Patient/" + pid},
       period: {start: row.encounter_date + "T09:00:00Z"}},
      {resourceType: "Observation", id: "OBS-" + pid, status: "final",
       code: {coding: [{system: "http://loinc.org", code: "2160-0", display: "Creatinine"}]},
       subject: {reference: "Patient/" + pid},
       encounter: {reference: "Encounter/" + eid},
       effectiveDateTime: row.encounter_date + "T09:00:00Z",
       valueQuantity: {value: row.creatinine_mg_dl, unit: "mg/dL",
                       system: "http://unitsofmeasure.org", code: "mg/dL"}},
    ];
    if (row.condition_code) {
      resources.push({resourceType: "Condition", id: "COND-" + pid,
        clinicalStatus: {coding: [{system: "http://terminology.hl7.org/CodeSystem/condition-clinical", code: "active"}]},
        code: {coding: [{system: "http://hl7.org/fhir/sid/icd-10-cm", code: row.condition_code, display: row.condition_display}]},
        subject: {reference: "Patient/" + pid},
        encounter: {reference: "Encounter/" + eid}});
    }
    for (const resource of resources) {
      entries.push({
        fullUrl: "https://example.invalid/fhir/" + resource.resourceType + "/" + resource.id,
        resource,
      });
    }
  }
  return {resourceType: "Bundle", type: "collection", entry: entries};
}

export function csvText(rows) {
  const safe = value => '"' + String(value ?? "").replaceAll('"', '""') + '"';
  return [COLUMNS.join(","), ...rows.map(row => COLUMNS.map(key => safe(row[key])).join(","))].join("\r\n") + "\r\n";
}

export function assessTask(input) {
  const primary = Number(input.primary_metric);
  const secondary = Number(input.secondary_metric);
  if (String(input.primary_metric).trim() === "" || String(input.secondary_metric).trim() === "" ||
      !Number.isFinite(primary) || !Number.isFinite(secondary)) {
    throw new Error("Primary and secondary metrics must be finite numbers.");
  }
  const status = String(input.status_descriptor || "").slice(0, 256).toUpperCase();
  const alerts = [];
  if (primary > 25) alerts.push({worker: "InvariantQCWorker", urgency: "ELEVATED_RISK", summary: "Primary metric exceeds example threshold 25"});
  if (input.is_critical_flag || secondary > 12) alerts.push({
    worker: "SafetyEscalationWorker",
    urgency: input.is_critical_flag ? "CRITICAL_STAT_PANIC" : "ELEVATED_RISK",
    summary: "Critical flag or secondary metric above example threshold 12",
  });
  if (["DISCORDANT", "ANOMALY", "MUTANT", "VIOLATION", "FAIL", "REJECT"].some(word => status.includes(word))) {
    alerts.push({worker: "ProtocolConformanceWorker", urgency: "ELEVATED_RISK", summary: "Example descriptor triggered"});
  }
  const urgency = alerts.some(a => a.urgency === "CRITICAL_STAT_PANIC") ? "CRITICAL_STAT_PANIC" :
    (alerts.length ? "ELEVATED_RISK" : "ROUTINE");
  return {mode: "browser-only-rule-demo", overall_urgency: urgency,
    integrity_status: urgency === "CRITICAL_STAT_PANIC" ? "RECALIBRATION_REQUIRED" :
      (urgency === "ELEVATED_RISK" ? "DISCORDANT_ANOMALY" : "VALIDATED_OPTIMAL"),
    total_alerts: alerts.length, alerts,
    notice: "These are arbitrary demonstration thresholds, not clinically validated rules. No signed audit ledger is created."};
}

function downloadFile(content, fileName, mime) {
  const url = URL.createObjectURL(new Blob([content], {type: mime}));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

if (typeof document !== "undefined") {
  let rows = null;
  const byId = id => document.getElementById(id);
  const message = byId("message");
  const report = byId("report");
  byId("generate-form").addEventListener("submit", event => {
    event.preventDefault();
    try {
      const count = parseCount(byId("count").value);
      const rawSeed = byId("seed").value.trim();
      const seed = rawSeed === "" ? Math.floor(Math.random() * 4294967296) : Number(rawSeed);
      rows = generateRows(count, seed);
      const bundle = makeBundle(rows);
      byId("record-count").textContent = String(rows.length);
      byId("resource-count").textContent = String(bundle.entry.length);
      byId("seed-used").textContent = String(seed);
      report.textContent = JSON.stringify({resourceType: "Bundle", type: "collection", entry: bundle.entry.slice(0, 8)}, null, 2);
      message.textContent = "Generated " + count + " synthetic patients locally. Preview shows the first eight resources.";
      byId("json-download").disabled = false;
      byId("csv-download").disabled = false;
    } catch (error) {
      rows = null;
      message.textContent = error.message;
      byId("json-download").disabled = true;
      byId("csv-download").disabled = true;
    }
  });
  byId("json-download").addEventListener("click", () => {
    if (rows) downloadFile(JSON.stringify(makeBundle(rows), null, 2) + "\n", "synthetic-ehr.json", "application/fhir+json");
  });
  byId("csv-download").addEventListener("click", () => {
    if (rows) downloadFile(csvText(rows), "synthetic-ehr.csv", "text/csv;charset=utf-8");
  });
  byId("audit-form").addEventListener("submit", event => {
    event.preventDefault();
    try {
      const result = assessTask({
        primary_metric: byId("primary").value,
        secondary_metric: byId("secondary").value,
        status_descriptor: byId("descriptor").value,
        is_critical_flag: byId("critical").checked,
      });
      byId("audit-report").textContent = JSON.stringify(result, null, 2);
    } catch (error) {
      byId("audit-report").textContent = error.message;
    }
  });
}

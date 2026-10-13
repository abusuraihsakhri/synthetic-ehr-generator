import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import {generateRows, makeBundle, csvText, assessTask, parseCount} from "../web/app.mjs";

test("deterministic seeded local generation with unique IDs", () => {
  const a = generateRows(50, 99);
  assert.deepEqual(a, generateRows(50, 99));
  assert.notDeepEqual(a, generateRows(50, 100));
  assert.equal(new Set(a.map(r => r.patient_id)).size, 50);
  assert.ok(a.every(r => r.creatinine_mg_dl >= 0.5 && r.creatinine_mg_dl <= 1.8));
});
test("count and seed bounds", () => {
  for (const n of [0, -1, 1001, 3.2, ""]) assert.throws(() => parseCount(n));
  assert.throws(() => generateRows(3, -1));
  assert.throws(() => generateRows(3, Infinity));
});
test("FHIR-shaped bundle references and CSV header", () => {
  const rows = generateRows(5, 20);
  const bundle = makeBundle(rows);
  assert.equal(bundle.resourceType, "Bundle");
  assert.equal(bundle.entry.filter(e => e.resource.resourceType === "Patient").length, 5);
  const urls = new Set(bundle.entry.map(e => e.fullUrl));
  assert.equal(urls.size, bundle.entry.length);
  const keys = new Set(bundle.entry.map(e => e.resource.resourceType + "/" + e.resource.id));
  for (const item of bundle.entry) {
    for (const prop of ["subject", "encounter"]) {
      if (item.resource[prop]) assert.ok(keys.has(item.resource[prop].reference));
    }
  }
  const csv = csvText(rows);
  assert.match(csv, /^patient_id,encounter_id,/);
  assert.equal(csv.trim().split("\n").length, 6);
});
test("demo thresholds match backend worker rules", () => {
  assert.equal(assessTask({primary_metric: 5, secondary_metric: 3}).overall_urgency, "ROUTINE");
  assert.equal(assessTask({primary_metric: 26, secondary_metric: 3}).overall_urgency, "ELEVATED_RISK");
  assert.equal(assessTask({primary_metric: 5, secondary_metric: 3, is_critical_flag: true}).overall_urgency, "CRITICAL_STAT_PANIC");
  assert.throws(() => assessTask({primary_metric: "", secondary_metric: "3"}));
});
test("HTML loads local module without external dependencies", () => {
  const html = readFileSync(new URL("../web/index.html", import.meta.url), "utf8");
  assert.match(html, /src="\.\/app\.mjs"/);
  assert.doesNotMatch(html, /https:\/\/fonts\.googleapis\.com/);
  assert.doesNotMatch(html, /HMAC_SHA256_e83f9a72/);
  assert.match(html, /id="json-download"/);
  assert.match(html, /id="csv-download"/);
});

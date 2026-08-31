import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  pathForDatasetView,
  pathForView,
  viewFromPath,
} from "../src/config/routing.ts";

test("clean URLs map to the expected application views", () => {
  assert.equal(viewFromPath("/"), "overview");
  assert.equal(viewFromPath("/overview"), "overview");
  assert.equal(viewFromPath("/qa-queue"), "qa-queue");
  assert.equal(viewFromPath("/qa-cases"), "qa-cases");
  assert.equal(viewFromPath("/real-data"), "overview");
  assert.equal(viewFromPath("/cases/LG-0001"), "case-detail");
  assert.equal(viewFromPath("/unknown"), "overview");
});

test("application views resolve to React Router paths", () => {
  assert.equal(pathForView("overview"), "/overview");
  assert.equal(pathForView("qa-queue"), "/qa-queue");
  assert.equal(pathForView("qa-cases"), "/qa-cases");
  assert.equal(pathForView("reports"), "/reports");
});

test("top-level API navigation keeps only the dataset scope", () => {
  assert.equal(
    pathForDatasetView("qa-cases", "nuscenes"),
    "/qa-cases?dataset=nuscenes",
  );
  assert.equal(pathForDatasetView("qa-queue"), "/qa-queue");
});

test("overview, reports and dataset runs render views without API-mode redirects", () => {
  const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

  assert.match(appSource, /location\.pathname === "\/"[\s\S]*?<LandingPage/);
  assert.match(appSource, /path="\/overview"[\s\S]*?<OverviewView/);
  assert.match(appSource, /path="\/reports" element={<ReportsView state={state} \/>}/);
  assert.match(appSource, /path="\/dataset-runs" element={<DatasetRunView \/>}/);
  assert.doesNotMatch(appSource, /path="\/reports"[^\n]*<Navigate/);
  assert.doesNotMatch(appSource, /path="\/dataset-runs"[^\n]*<Navigate/);
});

test("successful authentication navigates to the overview", () => {
  const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");

  assert.match(appSource, /await auth\.signIn\(email, password\);[\s\S]*?pathForDatasetView\("overview", cloudDatasetId\)/);
});

test("mock and Supabase login modes share the complete visual panel", () => {
  const mockLoginSource = readFileSync(new URL("../src/components/layout.tsx", import.meta.url), "utf8");
  const supabaseLoginSource = readFileSync(
    new URL("../src/components/AuthenticatedLoginScreen.tsx", import.meta.url),
    "utf8",
  );
  const visualPanelSource = readFileSync(
    new URL("../src/components/LoginVisualPanel.tsx", import.meta.url),
    "utf8",
  );

  assert.match(mockLoginSource, /<LoginVisualPanel \/>/);
  assert.match(supabaseLoginSource, /<LoginVisualPanel \/>/);
  assert.match(visualPanelSource, /className="visual-status"/);
  assert.match(visualPanelSource, /Protect every label\./);
  assert.match(visualPanelSource, /className="visual-metrics"/);
});

test("Supabase quick login creates a real token-backed session for each role", () => {
  const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  const loginSource = readFileSync(
    new URL("../src/components/AuthenticatedLoginScreen.tsx", import.meta.url),
    "utf8",
  );
  const authSource = readFileSync(
    new URL("../src/auth/AuthProvider.tsx", import.meta.url),
    "utf8",
  );
  const demoAuthSource = readFileSync(
    new URL("../src/auth/demoAuth.ts", import.meta.url),
    "utf8",
  );

  assert.match(
    loginSource,
    /const demoLoginRoles: Role\[\] = \["annotator", "reviewer", "admin"\]/,
  );
  assert.match(loginSource, /or sign in with Supabase/);
  assert.match(loginSource, /await onDemoSignIn\(role\)/);
  assert.match(appSource, /onDemoSignIn=\{handleDemoSignIn\}/);
  assert.match(appSource, /await auth\.signInDemo\(role\)/);
  assert.match(authSource, /getDemoAuthCredentials\(role\)/);
  assert.match(authSource, /signInWithPassword\(credentials\)/);
  assert.match(authSource, /expectedRole: role/);
  assert.match(authSource, /demoSessionRef\.current = true/);
  assert.match(authSource, /if \(supabase\) await supabase\.auth\.signOut\(\)/);
  assert.match(demoAuthSource, /VITE_SUPABASE_DEMO_ANNOTATOR_EMAIL/);
  assert.match(demoAuthSource, /VITE_SUPABASE_DEMO_REVIEWER_EMAIL/);
  assert.match(demoAuthSource, /VITE_SUPABASE_DEMO_ADMIN_EMAIL/);
});

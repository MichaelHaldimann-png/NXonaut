// NXonaut error-report relay: a Cloudflare Worker (free plan) that turns the anonymous
// reports of `nx_mcp.error_reports` into GitHub issues, one issue per fingerprint.
// Secret GITHUB_TOKEN: a fine-grained token with Issues read/write on this repo only.
// Setup: docs/error-reports.md. The token stays here; it never ships with NXonaut.

const REPO = "MichaelHaldimann-png/NXonaut";
const FIELDS = ["tool", "category", "code", "nx_code", "exception", "message",
  "nxonaut", "nx", "python", "os", "fingerprint", "count"];
const TOKEN = /^[\w.#: -]{0,60}$/;

function clean(input) {
  if (!input || typeof input !== "object") return null;
  const report = {};
  for (const key of FIELDS) {
    const value = input[key];
    if (value === undefined || value === null) { report[key] = null; continue; }
    if (key === "nx_code" || key === "count") {
      if (!Number.isInteger(value)) return null;
    } else if (typeof value !== "string" || (key === "message"
        ? value.length > 240 : !TOKEN.test(value))) {
      return null;
    }
    report[key] = value;
  }
  return /^[0-9a-f]{10}$/.test(report.fingerprint || "") && report.tool ? report : null;
}

async function github(env, path, init = {}) {
  return fetch(`https://api.github.com${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, "User-Agent": "nxonaut-relay",
      Accept: "application/vnd.github+json", "Content-Type": "application/json" },
  });
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("POST a report", { status: 405 });
    let report;
    try { report = clean(await request.json()); } catch { report = null; }
    if (!report) return new Response("rejected", { status: 400 });
    const body = "```json\n" + JSON.stringify(report, null, 1) + "\n```";
    const q = encodeURIComponent(`repo:${REPO} is:issue in:title ${report.fingerprint}`);
    const found = await (await github(env, `/search/issues?q=${q}`)).json();
    const issue = found.items && found.items[0];
    const answer = issue
      ? await github(env, `/repos/${REPO}/issues/${issue.number}/comments`,
          { method: "POST", body: JSON.stringify({ body: "Seen again:\n" + body }) })
      : await github(env, `/repos/${REPO}/issues`, { method: "POST", body: JSON.stringify({
          title: `[error-report] ${report.tool}: ${report.code} (${report.fingerprint})`,
          labels: ["error-report"],
          body: "Automatic, anonymous NXonaut error report (opt-in).\n\n" + body }) });
    return new Response(answer.ok ? "ok" : "github refused", { status: answer.ok ? 200 : 502 });
  },
};

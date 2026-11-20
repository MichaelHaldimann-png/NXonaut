# Error reports (opt-in, anonymous)

NXonaut can tell its maintainer when a tool fails on someone else's NX, so it gets
better on setups we never tested. It is **off** until the user says yes.

## For users

```powershell
python -m nx_mcp.error_reports ask      # the one question (the installer asks it)
python -m nx_mcp.error_reports status   # on or off, how many reports wait
python -m nx_mcp.error_reports list     # exactly what would be sent
python -m nx_mcp.error_reports send     # opens one prefilled GitHub issue per report
python -m nx_mcp.error_reports off      # off again; waiting reports are deleted
```

`NXONAUT_ERROR_REPORTS=off` in the environment turns it off whatever was answered (for a
company policy); `=on` turns it on without the question.

**What a report holds:** the tool name, error category and code, NX's numeric error
code, the exception type, NX's message with every quoted name, path, file name, e-mail,
user and computer name replaced by `<name>`, `<path>`, ... and the NXonaut, NX, Python
and Windows versions. **Never:** arguments, part or assembly names, file paths,
geometry, screenshots, tracebacks, user, computer or company names.

Only faults NXonaut should fix are kept (NX errors, failed geometry, solver, file,
bridge and rollback faults), not a wrong argument, a missing licence or the engineer's
own control. The same fault is one report with a count. Reports wait in
`<workspace>/.nx-mcp/error-reports.json`, which tools cannot read or change.

Without a relay, `send` opens the issue in the browser: the user sees the text, can edit
it and submits it with their own GitHub account. With a relay, a new report is sent in
the background as soon as it happens.

## For the maintainer: the relay (optional)

The relay files issues without the user needing a GitHub account. No GitHub token ever
ships with NXonaut: it stays in the relay.

1. Create a fine-grained GitHub token: only this repository, permission *Issues: read
   and write*.
2. Create a free Cloudflare Worker, paste `relay/error-report-worker.js`, and add the
   token as the secret `GITHUB_TOKEN`.
3. Put the Worker URL in `RELAY_URL` in `src/nx_mcp/error_reports.py` (or set
   `NXONAUT_REPORT_RELAY` for a test).

The relay accepts only the report fields above (short plain values, message at most 240
characters), and adds a comment to the existing issue when the fingerprint was seen
before. Issues carry the label `error-report`, which the weekly build reads.

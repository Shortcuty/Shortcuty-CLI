# Changelog

## 1.1.0 — 2026-10-15

- Sign local unsigned workflows with `shortcuty sign FILE`. Uploads and downloads
  stream without an API key; server filenames are sanitized, output is checked,
  and existing files stay protected unless `--force` is supplied.
- Set visibility, turn iOS 26 AI requirements off, clear optional fields, and send
  create/update requests as JSON or URL-encoded Form.
- Add request timeouts and clearer, redacted errors. Writes are never retried
  automatically; submission output shows scan and review state.
- Fix nullable descriptions, GIF screenshots, history and screenshot field names,
  update checks, and building wheels from source archives.
- Keep JSON output clean and retain existing commands, default JSON encoding,
  API-key configuration, and Python 3.8+ support.

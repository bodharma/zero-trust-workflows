# Changelog

## 1.0.0

- Added a supported V1 reusable Python 3.13 and uv 0.13.0 workflow with
  locked dependency installation and the caller's fixed `make check` command.
- Restricted workflow permissions to `contents: read`, with an
  `ubuntu-latest` runner and a 10-minute job timeout; no inputs or secrets.
- Pinned `actions/checkout` to `3d3c42e5aac5ba805825da76410c181273ba90b1` and
  `astral-sh/setup-uv` to `1c37ad07a6a961277cf70c0d37d6f313000f5884`.
- Added local workflow-policy validation, repository contract tests, public
  direct-reuse documentation, and an independent private-copy runbook.
- Tested workflow SHA: `f19cd36e55729ff60aea65c9b55474835127337c`.
  The direct-call example pins this immutable commit.
- Verified successful
  [canonical CI](https://github.com/bodharma/zero-trust-workflows/actions/runs/38059605717)
  at the tested workflow SHA and
  [consumer main CI](https://github.com/bodharma/zer_trust_infra/actions/runs/38060522185)
  at consumer commit `d68a9e1b50ee7b00111d5553e854915de5746a75`, whose caller
  pins the same tested workflow SHA.
- Require a committed `pyproject.toml`, `uv.lock`, and working `Makefile` with
  the caller's `check` target. Pass no secrets or `secrets: inherit`; the
  built-in `GITHUB_TOKEN` remains restricted to `contents: read`.
- Consumers must pin the full tested SHA, not the `v1.0.0` label. Review
  replacement workflow and action pins in a caller pull request and require
  passing CI before updating. Roll back by restoring the previous reviewed
  SHA in the caller and rerunning its CI.

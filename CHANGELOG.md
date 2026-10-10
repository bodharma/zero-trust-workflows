# Changelog

## Unreleased

- Added an experimental V1 reusable Python 3.13 and uv 0.13.0 workflow with
  locked dependency installation and the caller's fixed `make check` command.
- Restricted workflow permissions to `contents: read`, with an
  `ubuntu-latest` runner and a 10-minute job timeout; no inputs or secrets.
- Pinned `actions/checkout` to `3d3c42e5aac5ba805825da76410c181273ba90b1` and
  `astral-sh/setup-uv` to `1c37ad07a6a961277cf70c0d37d6f313000f5884`.
- Added local workflow-policy validation, repository contract tests, public
  direct-reuse documentation, and an independent private-copy runbook.
- Recorded the direct-call example's experimental workflow SHA as
  `d0789582c00aee75d1f63036b3bf364c9a977599`; a later supported release must
  record the reviewed SHA consumers should adopt.

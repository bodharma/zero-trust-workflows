# Changelog

## Unreleased

- Added `reusable-opentofu-check.yml` with fixed `make iac-check`, OpenTofu
  1.13.1, Terramate 0.17.3, uv 0.13.0, Python 3.13, SHA-pinned actions, and
  checksum-verified tool downloads. It has no cloud credentials, performs no
  live plan/apply or cloud API calls, and makes network requests only for pinned
  tool, Python dependency, and provider downloads. Callers must pin its reviewed
  full commit SHA and preserve this credential-free validation boundary.
- Documented every trusted-evidence object, the verified success and denial state
  transitions, exact local reproduction commands, coordinated rollback, and the
  current retention, public-metadata, archive, adapter, and deployment-identity limits.
- Recorded the accepted release, consumer trust policy, and main-branch acceptance run as
  separate reviewed links; workflow behavior and release tags are unchanged.

## 1.1.1

- Published signed [v1.1.1](https://github.com/bodharma/zero-trust-workflows/releases/tag/v1.1.1).
- Fixed the uv 0.13.0 assertion to accept its platform suffix while continuing
  to reject other versions and malformed prefixes. Workflow contracts,
  permissions, policies, tool versions, and action pins are unchanged.
- Tested workflow SHA: `0f9c834d44b63ba6587ad5c35434bd874629a687`.
  The trusted-evidence caller example pins this immutable commit in all three
  reusable workflow references.
- Accepted through successful
  [consumer main run 38134599975](https://github.com/bodharma/zer_trust_infra/actions/runs/38134599975)
  at consumer commit `d1101278d3d975f3b9d45113fdb2a14a94380737`, using Cosign
  v3.1.3 and the exact released-workflow certificate identity.
- Confirmed index-byte, evidence-byte, missing-evidence, wrong-identity, and
  wrong-commit mutations each exit 1 without creating promotion input.
- Audited Rekor log index `3206178263`: its API body matched the bundle and
  disclosed only the DSSE-envelope digest, payload digest, signature, and verifier
  certificate—not the evidence or predicate.
- Consumers must pin the full tested SHA, never the `v1.1.1` label. Immutable
  `v1.1.0` remains unchanged and is superseded by this correction.

## 1.1.0

- Published [v1.1.0](https://github.com/bodharma/zero-trust-workflows/releases/tag/v1.1.0).
- Added fixed reusable workflows for AMD64 Kubernetes conformance, main-push
  keyless evidence attestation, and independent signature and promotion-policy
  verification.
- Confined `id-token: write` to the attestation job and required exact
  repository, workflow, event, ref, issuer, predicate, and Cosign identity
  claims before promotion input can be produced.
- Tested workflow SHA: `f451d058ca9e052997a79e4fc041b051b1f7c942`.
  The trusted-evidence caller example pins this immutable commit in all three
  reusable workflow references.
- Consumers must pin the full tested SHA, never the `v1.1.0` label. Review the
  workflows, action pins, and consumer trust policy together; roll back by
  restoring the previous reviewed SHA in all three caller jobs.

## 1.0.1

- Published [v1.0.1](https://github.com/bodharma/zero-trust-workflows/releases/tag/v1.0.1).
  Immutable `v1.0.0` remains unchanged and is superseded by this correction.
- Enforced Python 3.13 selection through the existing pinned `astral-sh/setup-uv`
  action's `python-version: "3.13"` setting, retaining uv 0.13.0, locked
  dependency installation, and the caller's fixed `make check` command.
- Tested workflow SHA: `80c78d69c9a8aaf969420cfe690bdeae16b95879`.
  The direct-call example pins this immutable commit.
- Kept `contents: read`, no inputs or secrets, and the same external action pins:
  `actions/checkout` at `3d3c42e5aac5ba805825da76410c181273ba90b1` and
  `astral-sh/setup-uv` at `1c37ad07a6a961277cf70c0d37d6f313000f5884`.
- Verified successful
  [canonical CI](https://github.com/bodharma/zero-trust-workflows/actions/runs/38070964419)
  at the tested workflow SHA and
  [consumer main CI](https://github.com/bodharma/zer_trust_infra/actions/runs/38071226452)
  at consumer commit `e6dee7d7c8a8727a8bbd10f86bc44ef80cab2271`, whose caller
  pins the same tested workflow SHA.
- Consumers must pin the full tested SHA, never the `v1.0.1` label. Review the
  replacement workflow and action pins in a caller pull request and require
  passing CI before updating. Roll back by restoring the previous reviewed
  SHA in the caller and rerunning its CI.

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

# Security policy

Supported releases are documented in [CHANGELOG.md](CHANGELOG.md). No
response-time guarantee has been established. Review the pinned code and your
repository's execution boundary before use.

Report vulnerabilities through GitHub private vulnerability reporting at
[Report a vulnerability](https://github.com/bodharma/zero-trust-workflows/security/advisories/new).
Include the affected commit SHA, the impact, and a minimal reproduction with
synthetic data. If the private report option is unavailable, do not post the
report publicly; wait until the repository owner enables private reporting.

Never put secrets, credentials, or customer data in public issues, pull
requests, discussion threads, or workflow logs. Private reports should also
use redacted or synthetic examples. Rotate exposed credentials through the
owning system and report the affected workflow privately.

## Trusted-evidence security boundary

The trusted-evidence workflows use a split-authority design:

- conformance may execute consumer code but has only `contents: read`;
- attestation alone receives `id-token: write`, and only for an exact push to
  `refs/heads/main`;
- verification receives no signing authority and evaluates only a normalized
  input after exact Sigstore and evidence checks;
- deployment credentials and deployment commands are not part of this repository.

The main-only guard must remain identical in the caller and the reusable
attestation job. Removing either guard, granting OIDC to another job, adding a
secret/input contract, loosening an action SHA, or replacing an exact identity
with a regular expression is a security-sensitive contract change.

Artifacts are untrusted transport. `ztbp-evidence` is unsigned. Even
`ztbp-attested-evidence` must be rejected until verification confirms the modern
Sigstore bundle, exact certificate issuer and identity, repository context,
workflow, commit, event, ref, index bytes, evidence hashes, and catalog/gate
bindings. Never promote from artifact presence or a producer success status.

The workflows run `uv sync` and fixed `make` targets from the consumer checkout.
They do not sandbox malicious dependencies, build backends, Makefiles, Docker
builds, or test code. Version checks happen before consumer code, but a trusted
consumer revision and reviewed lock file are still required. GitHub-hosted
runners, GitHub's artifact/OIDC services, and every pinned third-party action
remain external dependencies in the threat model.

The seven-day retention is for debugging, not durable audit storage. Before
putting regulated or confidential fields into evidence, review the evidence and
Sigstore transparency-log disclosure model. Store long-term audit records in a
separately governed system, and never add raw credentials or customer data to
evidence, indexes, bundles, promotion inputs, artifact names, or logs.

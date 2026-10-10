# Zero Trust GitHub Workflows

`bodharma/zero-trust-workflows` provides one experimental V1 reusable GitHub
Actions workflow for Python repositories using uv. It checks out the caller's
repository, installs Python 3.13 and uv 0.13.0, runs `uv sync --locked --dev`,
and executes the caller's fixed `make check` target on `ubuntu-latest`, with a
10-minute job timeout.

## Prerequisites and local checks

The caller must supply a committed `pyproject.toml`, `uv.lock`, and a working
`Makefile` whose `check` target performs its required checks. There is no input
for changing the command, Python version, runner, or dependency installation.
To check this repository locally with uv installed:

```sh
uv sync --locked --dev && make check
```

Here, `make check` validates the workflow policy, runs pytest, and runs Ruff.

## Direct reuse

Copy [examples/direct-caller.yml](examples/direct-caller.yml) into your
repository's `.github/workflows/ci.yml`. It calls the public workflow by a full
40-character commit SHA, with `pull_request` and pushes to `main` as triggers
and only `contents: read` permissions. The reusable workflow executes against
the caller's code; the caller needs no fork or copy of this library.

Every external workflow or action reference must use a full 40-hex SHA, never
a mutable branch or tag. Review the workflow and its pinned actions before
adopting a SHA. The example currently pins the experimental commit
`d0789582c00aee75d1f63036b3bf364c9a977599`. No supported release exists yet;
consumers should adopt the later supported SHA recorded in a reviewed release.
Local `./` workflow references resolve at the same commit as the caller workflow.

## Trust boundary and non-goals

Do not pass secrets, use `secrets: inherit`, or add secret expressions. V1 has
no inputs, secret contract, deployment credentials, OIDC permissions, or
customer-specific configuration. GitHub still supplies its built-in
`GITHUB_TOKEN`, restricted here to reading repository contents. The workflow
runs the caller's dependency installation and `make check`; only run it on
code you are prepared to execute in that repository's CI boundary.

Deployment, infrastructure provisioning, cloud authentication, secret
management, and customizable build orchestration are outside V1. The local
policy validator checks workflow structure and references; it is not a secret
scanner, a sandbox, or proof that dependencies and shell commands are safe.
This experimental project does not yet promise a stable interface or production
support.

## Public copies and private isolation

Public GitHub forks remain public; a fork of this public repository cannot be
made private independently. Public forks share Git data within their network.
A local clone is a working copy, and its remotes determine where later pushes
go; cloning does not create an independent private GitHub repository. See
[GitHub's fork visibility documentation](https://docs.github.com/en/pull-requests/reference/forks).

For organization-specific changes, use the
[independent private-copy runbook](examples/isolated-copy.md). Create an empty
private repository outside the public fork network, import reviewed code, and
keep public-upstream access fetch-only. Direct reuse, public collaboration,
and independent private copies are separate distribution choices.

## Reporting and license

Follow [SECURITY.md](SECURITY.md) for private vulnerability reports. Changes are
recorded in [CHANGELOG.md](CHANGELOG.md). Copyright 2026 bodharma. This project
is licensed under [Apache-2.0](LICENSE).

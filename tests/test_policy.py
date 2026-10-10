import subprocess
import sys
from pathlib import Path
from shutil import copyfile

import pytest
import yaml

from ztwf import validate
from ztwf.validate import validate_repository

FIXTURES = Path(__file__).parent / "fixtures"
SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
ATTESTATION_WORKFLOW = ".github/workflows/reusable-evidence-attestation.yml"
ATTESTATION_USES = (
    "bodharma/zero-trust-workflows/.github/workflows/"
    f"reusable-evidence-attestation.yml@{SHA}"
)
MAIN_PUSH_GUARD = "github.event_name == 'push' && github.ref == 'refs/heads/main'"


def test_empty_repository_is_invalid(tmp_path):
    assert validate_repository(tmp_path) == [
        "repository: no workflow or composite-action documents found"
    ]


@pytest.mark.parametrize("kind", ["workflow", "action"])
@pytest.mark.parametrize("extension", ["yml", "yaml"])
def test_valid_documents_pass(tmp_path, kind, extension):
    relative = (
        f".github/workflows/check.{extension}"
        if kind == "workflow"
        else f"actions/nested/check/action.{extension}"
    )
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    copyfile(FIXTURES / "valid" / f"{kind}.yml", path)
    assert validate_repository(tmp_path) == []


@pytest.mark.parametrize(
    ("fixture", "relative"),
    [
        ("reusable-evidence-attestation.yml", ATTESTATION_WORKFLOW),
        ("evidence-attestation-caller.yml", ".github/workflows/evidence.yml"),
    ],
)
def test_valid_oidc_workflows_pass_only_in_the_attestation_chain(tmp_path, fixture, relative):
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    copyfile(FIXTURES / "valid" / fixture, path)
    assert validate_repository(tmp_path) == []


@pytest.mark.parametrize(
    ("fixture", "relative", "expected"),
    [
        ("root.yml", ".github/workflows/check.yml", "name: expected a non-empty string"),
        (
            "permissions.yml",
            ".github/workflows/check.yml",
            "permissions: expected {} or {contents: read}",
        ),
        ("secrets.yml", ".github/workflows/check.yml", "secrets: secrets are forbidden"),
        (
            "trigger.yml",
            ".github/workflows/check.yml",
            "on: expected only workflow_call, pull_request, or push",
        ),
        (
            "uses.yml",
            ".github/workflows/check.yml",
            "jobs.check.steps[0].uses: expected a safe local path or a full 40-hex SHA",
        ),
        (
            "runner.yml",
            ".github/workflows/check.yml",
            "jobs.check.runs-on: expected ubuntu-latest",
        ),
        (
            "timeout.yml",
            ".github/workflows/check.yml",
            "jobs.check.timeout-minutes: expected an integer from 1 through 30",
        ),
        (
            "caller.yml",
            ".github/workflows/check.yml",
            "jobs.check: caller jobs allow only uses, permissions, needs, if, and with",
        ),
        (
            "shell.yml",
            ".github/workflows/check.yml",
            "jobs.check.steps[0].run: shell expressions are forbidden",
        ),
        ("action.yml", "actions/check/action.yml", "runs.using: expected composite"),
        (
            "composite.yml",
            "actions/check/action.yml",
            "runs.steps[0].uses: expected a safe local path or a full 40-hex SHA",
        ),
    ],
)
def test_invalid_fixtures_fail_closed(tmp_path, fixture, relative, expected):
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    copyfile(FIXTURES / "invalid" / fixture, path)
    issues = validate_repository(tmp_path)
    assert f"{relative}: {expected}" in issues
    assert issues == sorted(issues)
    assert all(issue.startswith(f"{relative}: ") for issue in issues)


@pytest.mark.parametrize(
    ("fixture", "relative", "expected"),
    [
        (
            "workflow-oidc.yml",
            ATTESTATION_WORKFLOW,
            "permissions: expected {} or {contents: read}",
        ),
        (
            "pr-triggered-oidc.yml",
            ATTESTATION_WORKFLOW,
            "jobs.attest.permissions: expected {} or {contents: read}",
        ),
        (
            "other-workflow-oidc.yml",
            ".github/workflows/other.yml",
            "jobs.attest.permissions: expected {} or {contents: read}",
        ),
        (
            "other-job-oidc.yml",
            ATTESTATION_WORKFLOW,
            "jobs.sign.permissions: expected {} or {contents: read}",
        ),
        (
            "write-permissions.yml",
            ".github/workflows/write-permissions.yml",
            "jobs.actions.permissions: expected {} or {contents: read}",
        ),
        (
            "write-permissions.yml",
            ".github/workflows/write-permissions.yml",
            "jobs.contents.permissions: expected {} or {contents: read}",
        ),
        (
            "secret-input.yml",
            ".github/workflows/secret-input.yml",
            "jobs.attest.with.token: secret expressions are forbidden",
        ),
        (
            "inherit-secrets.yml",
            ".github/workflows/inherit-secrets.yml",
            "jobs.attest.secrets: secrets are forbidden",
        ),
        (
            "mutable-action-ref.yml",
            ".github/workflows/mutable-action-ref.yml",
            "jobs.check.steps[0].uses: expected a safe local path or a full 40-hex SHA",
        ),
        (
            "conformance-caller-oidc.yml",
            ".github/workflows/conformance-caller.yml",
            "jobs.conformance.permissions: expected {} or {contents: read}",
        ),
        (
            "verification-caller-oidc.yml",
            ".github/workflows/verification-caller.yml",
            "jobs.verify.permissions: expected {} or {contents: read}",
        ),
        (
            "insecure-cosign.yml",
            ".github/workflows/insecure-cosign.yml",
            "jobs.check.steps[0].run: prohibited Cosign flag --insecure-ignore-tlog",
        ),
    ],
)
def test_oidc_and_caller_policy_fixtures_fail_closed(tmp_path, fixture, relative, expected):
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    copyfile(FIXTURES / "invalid" / fixture, path)
    issues = validate_repository(tmp_path)
    assert f"{relative}: {expected}" in issues
    assert issues == sorted(issues)


@pytest.mark.parametrize("value", [{}, {"contents": "read"}])
def test_restrictive_permissions_pass(value):
    assert validate.validate_permissions(value, "workflow: permissions") == []


@pytest.mark.parametrize(
    "value",
    [
        None,
        "read-all",
        "write-all",
        {"contents": "write"},
        {"id-token": "write"},
        {"issues": "read"},
        {"contents": "read", "actions": "read"},
        [],
    ],
)
def test_other_permissions_fail(value):
    assert validate.validate_permissions(value, "workflow: permissions") == [
        "workflow: permissions: expected {} or {contents: read}"
    ]


@pytest.mark.parametrize(
    "value",
    [f"actions/checkout@{SHA}", f"owner/repo/path@{SHA.upper()}", "./action", "./.github/a.yml"],
)
def test_immutable_or_local_uses_pass(value):
    assert validate.validate_uses(value, "workflow: uses") == []


@pytest.mark.parametrize(
    "value",
    [
        "actions/checkout@main",
        "actions/checkout@v4",
        "actions/checkout@1234567",
        "docker://alpine:3",
        f"repo@{SHA}",
        f"owner/repo@{SHA}0",
        "./../action",
        "./a/../action",
        "/action",
        "../action",
        "https://example.com/action",
        None,
        123,
    ],
)
def test_unsafe_uses_fail(value):
    assert validate.validate_uses(value, "workflow: uses") == [
        "workflow: uses: expected a safe local path or a full 40-hex SHA"
    ]


def workflow_document():
    return {
        "name": "check",
        "on": {"workflow_call": None},
        "permissions": {"contents": "read"},
        "jobs": {
            "check": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "steps": [{"run": "make check"}],
            }
        },
    }


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("name", None, "name: expected a non-empty string"),
        ("name", "", "name: expected a non-empty string"),
        ("on", None, "on: expected only workflow_call, pull_request, or push"),
        ("on", [], "on: expected only workflow_call, pull_request, or push"),
        ("on", "pull_request_target", "on: expected only workflow_call, pull_request, or push"),
        ("on", {"schedule": []}, "on: expected only workflow_call, pull_request, or push"),
        ("jobs", {}, "jobs: expected a non-empty mapping"),
        ("jobs", [], "jobs: expected a non-empty mapping"),
    ],
)
def test_required_workflow_fields(field, value, expected):
    document = workflow_document()
    document[field] = value
    assert f"workflow: {expected}" in validate.validate_workflow(document, "workflow")


@pytest.mark.parametrize("field", ["name", "on", "jobs", "permissions"])
def test_missing_workflow_fields_fail(field):
    document = workflow_document()
    del document[field]
    assert validate.validate_workflow(document, "workflow")


@pytest.mark.parametrize("trigger", ["workflow_call", "pull_request", "push"])
@pytest.mark.parametrize("shape", ["string", "list", "mapping"])
def test_supported_trigger_forms_pass(trigger, shape):
    document = workflow_document()
    document["on"] = {"string": trigger, "list": [trigger], "mapping": {trigger: None}}[shape]
    assert validate.validate_workflow(document, "workflow") == []


@pytest.mark.parametrize("value", ["self-hosted", ["ubuntu-latest"], "${{ inputs.runner }}", None])
def test_untrusted_runners_fail(value):
    document = workflow_document()
    document["jobs"]["check"]["runs-on"] = value
    assert "workflow: jobs.check.runs-on: expected ubuntu-latest" in (
        validate.validate_workflow(document, "workflow")
    )


@pytest.mark.parametrize("value", [None, 0, 31, True, 1.5, "10"])
def test_invalid_timeouts_fail(value):
    document = workflow_document()
    document["jobs"]["check"]["timeout-minutes"] = value
    assert "workflow: jobs.check.timeout-minutes: expected an integer from 1 through 30" in (
        validate.validate_workflow(document, "workflow")
    )


@pytest.mark.parametrize("value", [1, 30])
def test_timeout_boundaries_pass(value):
    document = workflow_document()
    document["jobs"]["check"]["timeout-minutes"] = value
    assert validate.validate_workflow(document, "workflow") == []


@pytest.mark.parametrize("value", [None, [], {}, "run"])
def test_empty_or_wrong_typed_steps_fail(value):
    assert validate.validate_steps(value, "workflow: steps") == [
        "workflow: steps: expected a non-empty list"
    ]


@pytest.mark.parametrize(
    "value",
    [None, "run", {}, {"run": True}, {"uses": None}, {"run": "echo ok", "uses": "./action"}],
)
def test_invalid_steps_fail(value):
    assert validate.validate_steps([value], "workflow: steps")


@pytest.mark.parametrize("extra", [{}, {"permissions": {}}, {"permissions": {"contents": "read"}}])
def test_reusable_caller_jobs_pass(extra):
    document = workflow_document()
    document["jobs"] = {"check": {"uses": "./.github/workflows/reusable.yml", **extra}}
    assert validate.validate_workflow(document, "workflow") == []


@pytest.mark.parametrize(
    "needs",
    ["conformance", ["conformance"], ["conformance", "policy-check"]],
)
def test_reusable_caller_consumer_chain_fields_pass(needs):
    document = workflow_document()
    document["jobs"] = {
        "attest": {
            "uses": "./.github/workflows/reusable.yml",
            "needs": needs,
            "if": "github.ref == 'refs/heads/main'",
            "with": {"artifact": "ztbp-evidence"},
        }
    }
    assert validate.validate_workflow(document, "workflow") == []


@pytest.mark.parametrize(
    "needs", [None, "", " ", "not a job", [], ["check", "check"], ["check", ""]]
)
def test_reusable_caller_needs_must_name_unique_jobs(needs):
    document = workflow_document()
    document["jobs"] = {"check": {"uses": "./.github/workflows/reusable.yml", "needs": needs}}
    assert "workflow: jobs.check.needs: expected a job name or non-empty unique list" in (
        validate.validate_workflow(document, "workflow")
    )


@pytest.mark.parametrize(
    "condition",
    [
        None,
        True,
        "",
        " ",
        "${{ secrets.TOKEN }}",
        "secrets.TOKEN != ''",
        "SECRETS ['TOKEN'] != ''",
    ],
)
def test_reusable_caller_if_must_be_a_non_secret_literal(condition):
    document = workflow_document()
    document["jobs"] = {
        "check": {"uses": "./.github/workflows/reusable.yml", "if": condition}
    }
    assert "workflow: jobs.check.if: expected a non-empty literal without secrets" in (
        validate.validate_workflow(document, "workflow")
    )


@pytest.mark.parametrize(
    "inputs",
    [None, [], "artifact", {"token": "${{ secrets.TOKEN }}"}, {"${{ secrets.KEY }}": "value"}],
)
def test_reusable_caller_with_must_be_a_non_secret_mapping(inputs):
    document = workflow_document()
    document["jobs"] = {
        "check": {"uses": "./.github/workflows/reusable.yml", "with": inputs}
    }
    assert "workflow: jobs.check.with: expected a mapping without secret expressions" in (
        validate.validate_workflow(document, "workflow")
    )


def test_reusable_caller_with_recursive_alias_finishes_validation():
    inputs = {}
    inputs["loop"] = inputs
    document = workflow_document()
    document["jobs"] = {
        "check": {"uses": "./.github/workflows/reusable.yml", "with": inputs}
    }
    assert validate.validate_workflow(document, "workflow") == []


def test_attestation_caller_oidc_requires_exact_pinned_workflow_and_main_push_guard():
    document = workflow_document()
    document["on"] = "push"
    document["jobs"] = {
        "attest": {
            "uses": ATTESTATION_USES,
            "permissions": {"contents": "read", "id-token": "write"},
            "if": MAIN_PUSH_GUARD,
        }
    }
    assert validate.validate_workflow(document, "workflow") == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("on", "pull_request"),
        ("uses", f"bodharma/zero-trust-workflows/.github/workflows/reusable-conformance.yml@{SHA}"),
        ("uses", "./.github/workflows/reusable-evidence-attestation.yml"),
        ("if", f"${{{{ {MAIN_PUSH_GUARD} }}}}"),
        ("if", "github.ref == 'refs/heads/main' && github.event_name == 'push'"),
        ("if", f"({MAIN_PUSH_GUARD})"),
    ],
)
def test_attestation_caller_oidc_rejects_every_non_exact_precondition(field, value):
    document = workflow_document()
    document["on"] = "push"
    job = {
        "uses": ATTESTATION_USES,
        "permissions": {"contents": "read", "id-token": "write"},
        "if": MAIN_PUSH_GUARD,
    }
    if field == "on":
        document["on"] = value
    else:
        job[field] = value
    document["jobs"] = {"attest": job}
    assert "workflow: jobs.attest.permissions: expected {} or {contents: read}" in (
        validate.validate_workflow(document, "workflow")
    )


@pytest.mark.parametrize("field", ["runs-on", "steps", "secrets", "env", "continue-on-error"])
def test_caller_jobs_reject_additional_fields(field):
    document = workflow_document()
    document["jobs"] = {"check": {"uses": "./.github/workflows/reusable.yml", field: True}}
    assert "workflow: jobs.check: caller jobs allow only uses, permissions, needs, if, and with" in (
        validate.validate_workflow(document, "workflow")
    )


@pytest.mark.parametrize(
    "flag",
    [
        "--insecure-ignore-tlog",
        "--insecure-ignore-sct",
        "--check-claims=false",
        "--certificate-identity-regexp",
        "--certificate-oidc-issuer-regexp",
    ],
)
def test_insecure_cosign_flags_are_rejected(flag):
    assert f"workflow: steps[0].run: prohibited Cosign flag {flag}" in validate.validate_steps(
        [{"run": f"cosign verify {flag} value evidence-index.json"}], "workflow: steps"
    )


@pytest.mark.parametrize("using", [None, "node20", "docker", 123])
def test_non_composite_actions_fail(using):
    assert validate.validate_action({"runs": {"using": using}}, "action")


@pytest.mark.parametrize(
    ("addition", "expected"),
    [
        ({"secrets": "inherit"}, "secrets: secrets are forbidden"),
        ({"env": {"TOKEN": "${{ secrets.TOKEN }}"}}, "env.TOKEN: secret expressions are forbidden"),
        ({"env": {"TOKEN": "${{secrets.TOKEN}}"}}, "env.TOKEN: secret expressions are forbidden"),
        (
            {"env": {"TOKEN": "${{ secrets['TOKEN'] }}"}},
            "env.TOKEN: secret expressions are forbidden",
        ),
        (
            {"env": {"${{ secrets.TOKEN }}": "value"}},
            "env.${{ secrets.TOKEN }}: secret expressions are forbidden",
        ),
        (
            {"nested": [{"run": "echo ${{ github.event.pull_request.title }}"}]},
            "nested[0].run: shell expressions are forbidden",
        ),
    ],
)
def test_security_scan_reaches_nested_values(tmp_path, addition, expected):
    document = workflow_document()
    document.update(addition)
    path = tmp_path / ".github/workflows/check.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(document))
    assert f".github/workflows/check.yml: {expected}" in validate_repository(tmp_path)


def test_issues_are_sorted_across_documents(tmp_path):
    directory = tmp_path / ".github/workflows"
    directory.mkdir(parents=True)
    for filename in ["z.yml", "a.yml"]:
        (directory / filename).write_text("name: 1\n")
    issues = validate_repository(tmp_path)
    assert issues and issues == sorted(issues)


@pytest.mark.parametrize(
    "expression",
    [
        "${{ true && secrets.TOKEN }}",
        "${{ toJSON(secrets) }}",
        "${{ secrets ['TOKEN'] }}",
        "${{\n true &&\n secrets.TOKEN\n }}",
        "${{ format('}}', secrets.TOKEN) }}",
        "${{ toJSON(SECRETS) }}",
    ],
)
def test_secret_context_anywhere_in_expressions_fails(tmp_path, expression):
    document = workflow_document()
    document["env"] = {"TOKEN": expression}
    path = tmp_path / ".github/workflows/check.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(document))
    assert validate_repository(tmp_path) == [
        ".github/workflows/check.yml: env.TOKEN: secret expressions are forbidden"
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Documentation mentions secrets.TOKEN",
        "${{ github.ref }} then secrets.TOKEN",
        "${{ 'secrets.TOKEN' }}",
    ],
)
def test_secret_prose_outside_expressions_passes(tmp_path, text):
    document = workflow_document()
    document["description"] = text
    path = tmp_path / ".github/workflows/check.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(document))
    assert validate_repository(tmp_path) == []


def test_long_escaped_expression_literal_finishes_validation(tmp_path):
    document = workflow_document()
    document["env"] = {"TEXT": "${{ '" + "''" * 256 + "' }}"}
    path = tmp_path / ".github/workflows/check.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(document))
    result = subprocess.run(
        [sys.executable, "-m", "ztwf", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("expression", ["${{ vars.SECRETS }}", "${{ vars['SECRETS'] }}"])
def test_properties_of_other_contexts_pass(tmp_path, expression):
    document = workflow_document()
    document["env"] = {"TEXT": expression}
    path = tmp_path / ".github/workflows/check.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(document))
    assert validate_repository(tmp_path) == []

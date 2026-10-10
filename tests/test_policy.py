from pathlib import Path
from shutil import copyfile

import pytest
import yaml

from ztwf import validate
from ztwf.validate import validate_repository

FIXTURES = Path(__file__).parent / "fixtures"
SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"


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
            "jobs.check: caller jobs allow only uses and permissions",
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


@pytest.mark.parametrize("field", ["runs-on", "steps", "secrets", "env", "continue-on-error"])
def test_caller_jobs_reject_additional_fields(field):
    document = workflow_document()
    document["jobs"] = {"check": {"uses": "./.github/workflows/reusable.yml", field: True}}
    assert "workflow: jobs.check: caller jobs allow only uses and permissions" in (
        validate.validate_workflow(document, "workflow")
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

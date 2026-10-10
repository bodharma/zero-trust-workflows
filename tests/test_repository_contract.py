import re
from pathlib import Path

import pytest

from ztwf.validate import load_document, validate_workflow

ROOT = Path(__file__).resolve().parents[1]
REUSABLE = ".github/workflows/reusable-python-uv-check.yml"
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_UV = "astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884"
DIRECT_CALLER = "examples/direct-caller.yml"
SUPPORTED_SHA = "f19cd36e55729ff60aea65c9b55474835127337c"


def test_reusable_workflow_has_the_fixed_check_contract():
    workflow, issues = load_document(ROOT, ROOT / REUSABLE)
    assert issues == []
    assert set(workflow) == {"name", "on", "permissions", "jobs"}
    assert workflow["name"] == "reusable-python-uv-check"
    assert workflow["on"] == {"workflow_call": None}
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"check"}
    job = workflow["jobs"]["check"]
    assert set(job) == {"runs-on", "timeout-minutes", "steps"}
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == 10
    steps = job["steps"]
    assert steps[:2] == [
        {"uses": CHECKOUT},
        {
            "uses": SETUP_UV,
            "with": {"version": "0.13.0", "python-version": "3.13", "enable-cache": True},
        },
    ]
    assert [step.get("run") for step in steps if "run" in step] == [
        "uv python install 3.13",
        "uv sync --locked --dev",
        "make check",
    ]
    assert len(steps) == 5
    assert all(set(step) == {"run"} for step in steps[2:])


def test_self_ci_only_calls_the_reusable_workflow():
    workflow, issues = load_document(ROOT, ROOT / ".github/workflows/ci.yml")
    assert issues == []
    assert set(workflow) == {"name", "on", "permissions", "jobs"}
    assert workflow["on"] == {"pull_request": None, "push": {"branches": ["main"]}}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"] == {"check": {"uses": f"./{REUSABLE}"}}


def test_direct_caller_pins_the_supported_workflow_with_the_self_ci_contract():
    workflow, issues = load_document(ROOT, ROOT / DIRECT_CALLER)
    assert issues == []
    assert validate_workflow(workflow, DIRECT_CALLER) == []
    assert workflow == {
        "name": "ci",
        "on": {"pull_request": None, "push": {"branches": ["main"]}},
        "permissions": {"contents": "read"},
        "jobs": {
            "check": {"uses": f"bodharma/zero-trust-workflows/{REUSABLE}@{SUPPORTED_SHA}"}
        },
    }
    assert re.findall(r"\b[0-9a-fA-F]{40}\b", (ROOT / DIRECT_CALLER).read_text()) == [
        SUPPORTED_SHA
    ]


def test_changelog_records_the_same_supported_workflow_sha():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    release = re.search(r"^## 1\.0\.0\n(.*?)(?=^## |\Z)", changelog, re.MULTILINE | re.DOTALL)
    assert release is not None
    assert re.findall(r"Tested workflow SHA: `([0-9a-f]{40})`", release[1]) == [SUPPORTED_SHA]


@pytest.mark.parametrize("relative", [REUSABLE, ".github/workflows/ci.yml", DIRECT_CALLER])
def test_workflows_have_no_inputs_secrets_env_or_failure_suppression(relative):
    workflow, issues = load_document(ROOT, ROOT / relative)
    assert issues == []
    pending = [workflow]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            assert not {"inputs", "secrets", "env", "continue-on-error"}.intersection(value)
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)

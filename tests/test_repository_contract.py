import re
from pathlib import Path

import pytest

from ztwf.validate import load_document, validate_workflow

ROOT = Path(__file__).resolve().parents[1]
REUSABLE = ".github/workflows/reusable-python-uv-check.yml"
CONFORMANCE = ".github/workflows/reusable-conformance.yml"
ATTESTATION = ".github/workflows/reusable-evidence-attestation.yml"
VERIFICATION = ".github/workflows/reusable-evidence-verification.yml"
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
TRUSTED_CHECKOUT = {"uses": CHECKOUT, "with": {"persist-credentials": False}}
SETUP_UV = "astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884"
UPLOAD = "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
DOWNLOAD = "actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333"
SETUP_COSIGN = "sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6"
SETUP_KUBECTL = "azure/setup-kubectl@bda439f5f36b99b262ebdcd3613869bddb064c8e"
DIRECT_CALLER = "examples/direct-caller.yml"
TRUSTED_EVIDENCE_CALLER = "examples/trusted-evidence-caller.yml"
SUPPORTED_SHA = "80c78d69c9a8aaf969420cfe690bdeae16b95879"
TRUSTED_EVIDENCE_SHA = "f451d058ca9e052997a79e4fc041b051b1f7c942"
MAIN_GUARD = "github.event_name == 'push' && github.ref == 'refs/heads/main'"
UV_PYTHON_VERSION_CHECK = """uv --version
uv --version | grep -Eq '^uv 0\\.13\\.0([[:space:]]|$)'
uv run --no-project --python 3.13 python --version
uv run --no-project --python 3.13 python -c 'import sys; assert sys.version_info[:2] == (3, 13)'
"""


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


def test_reusable_conformance_has_the_fixed_trusted_evidence_contract():
    workflow, issues = load_document(ROOT, ROOT / CONFORMANCE)
    assert issues == []
    assert workflow == {
        "name": "reusable-conformance",
        "on": {"workflow_call": None},
        "permissions": {"contents": "read"},
        "jobs": {
            "conformance": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 30,
                "steps": [
                    TRUSTED_CHECKOUT,
                    {
                        "uses": SETUP_UV,
                        "with": {
                            "version": "0.13.0",
                            "python-version": "3.13",
                            "enable-cache": True,
                        },
                    },
                    {"run": "uv python install 3.13"},
                    {
                        "run": (
                            "curl --fail --location --proto '=https' --tlsv1.2 "
                            "--output /tmp/kind "
                            "https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-amd64\n"
                            "echo \"aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d"
                            "  /tmp/kind\" | sha256sum --check --strict\n"
                            "sudo install -m 0755 /tmp/kind /usr/local/bin/kind\n"
                        )
                    },
                    {
                        "uses": SETUP_KUBECTL,
                        "with": {
                            "version": "v1.35.9",
                            "checksum": (
                                "3cfeaf80be482b435b0aa214aff6e0b2c312ee23c0ff20810c75517b6004c6eb"
                            ),
                        },
                    },
                    {
                        "run": UV_PYTHON_VERSION_CHECK
                        + "kind version\n"
                        + "kind version | grep -Eq '^kind v0\\.33\\.0([[:space:]]|$)'\n"
                        + "kubectl version --client\n"
                        + "kubectl version --client | grep -Fx 'Client Version: v1.35.9'\n"
                    },
                    {"run": "uv sync --locked --dev"},
                    {"run": "make trusted-evidence"},
                    {
                        "uses": UPLOAD,
                        "with": {
                            "name": "ztbp-evidence",
                            "path": ".artifacts/trusted/evidence",
                            "retention-days": 7,
                            "if-no-files-found": "error",
                            "include-hidden-files": True,
                        },
                    },
                ],
            }
        },
    }


def test_reusable_attestation_has_the_fixed_main_only_contract():
    workflow, issues = load_document(ROOT, ROOT / ATTESTATION)
    assert issues == []
    assert workflow == {
        "name": "reusable-evidence-attestation",
        "on": {"workflow_call": None},
        "permissions": {"contents": "read"},
        "jobs": {
            "attest": {
                "if": MAIN_GUARD,
                "permissions": {"contents": "read", "id-token": "write"},
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "steps": [
                    TRUSTED_CHECKOUT,
                    {
                        "uses": SETUP_UV,
                        "with": {
                            "version": "0.13.0",
                            "python-version": "3.13",
                            "enable-cache": True,
                        },
                    },
                    {"run": "uv python install 3.13"},
                    {"uses": SETUP_COSIGN, "with": {"cosign-release": "v3.1.3"}},
                    {
                        "run": UV_PYTHON_VERSION_CHECK
                        + "cosign version\n"
                        + "cosign version --json | uv run --no-project --python 3.13 "
                        + "python -c 'import json,sys; assert json.load(sys.stdin)[\"gitVersion\"] "
                        + "== \"v3.1.3\"'\n"
                    },
                    {"run": "uv sync --locked --dev"},
                    {
                        "uses": DOWNLOAD,
                        "with": {
                            "name": "ztbp-evidence",
                            "path": ".artifacts/trusted/evidence",
                        },
                    },
                    {
                        "run": (
                            "uv run --locked ztbp-evidence attest --root . "
                            "--evidence-root .artifacts/trusted/evidence "
                            "--trust-policy trust/github-main.yaml "
                            "--index .artifacts/trusted/evidence-index.json "
                            "--bundle .artifacts/trusted/evidence-index.sigstore.json"
                        )
                    },
                    {
                        "uses": UPLOAD,
                        "with": {
                            "name": "ztbp-attested-evidence",
                            "path": (
                                ".artifacts/trusted/evidence\n"
                                ".artifacts/trusted/evidence-index.json\n"
                                ".artifacts/trusted/evidence-index.sigstore.json"
                            ),
                            "retention-days": 7,
                            "if-no-files-found": "error",
                            "include-hidden-files": True,
                        },
                    },
                ],
            }
        },
    }


def test_reusable_verification_has_the_fixed_promotion_contract():
    workflow, issues = load_document(ROOT, ROOT / VERIFICATION)
    assert issues == []
    assert workflow == {
        "name": "reusable-evidence-verification",
        "on": {"workflow_call": None},
        "permissions": {"contents": "read"},
        "jobs": {
            "verify": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "steps": [
                    TRUSTED_CHECKOUT,
                    {
                        "uses": SETUP_UV,
                        "with": {
                            "version": "0.13.0",
                            "python-version": "3.13",
                            "enable-cache": True,
                        },
                    },
                    {"run": "uv python install 3.13"},
                    {"uses": SETUP_COSIGN, "with": {"cosign-release": "v3.1.3"}},
                    {
                        "run": UV_PYTHON_VERSION_CHECK
                        + "cosign version\n"
                        + "cosign version --json | uv run --no-project --python 3.13 "
                        + "python -c 'import json,sys; assert json.load(sys.stdin)[\"gitVersion\"] "
                        + "== \"v3.1.3\"'\n"
                    },
                    {"run": "uv sync --locked --dev"},
                    {
                        "uses": DOWNLOAD,
                        "with": {
                            "name": "ztbp-attested-evidence",
                            "path": ".artifacts/trusted",
                        },
                    },
                    {
                        "run": (
                            "uv run --locked ztbp-evidence verify --root . "
                            "--evidence-root .artifacts/trusted/evidence "
                            "--trust-policy trust/github-main.yaml --gate main-conformance "
                            "--index .artifacts/trusted/evidence-index.json "
                            "--bundle .artifacts/trusted/evidence-index.sigstore.json "
                            "--output .artifacts/trusted/promotion-input.json"
                        )
                    },
                    {
                        "run": (
                            "make promotion-check "
                            "PROMOTION_INPUT=.artifacts/trusted/promotion-input.json"
                        )
                    },
                    {
                        "uses": UPLOAD,
                        "with": {
                            "name": "ztbp-promotion-input",
                            "path": ".artifacts/trusted/promotion-input.json",
                            "retention-days": 7,
                            "if-no-files-found": "error",
                            "include-hidden-files": True,
                        },
                    },
                ],
            }
        },
    }


def test_trusted_workflows_confine_oidc_and_forbid_configurable_or_secret_data():
    oidc_locations = []
    for relative in (CONFORMANCE, ATTESTATION, VERIFICATION):
        workflow, issues = load_document(ROOT, ROOT / relative)
        assert issues == []
        pending = [(workflow, relative)]
        while pending:
            value, location = pending.pop()
            if isinstance(value, dict):
                assert not {
                    "inputs",
                    "secrets",
                    "env",
                    "continue-on-error",
                }.intersection(value)
                if value.get("id-token") == "write":
                    oidc_locations.append(location)
                pending.extend((nested, f"{location}.{key}") for key, nested in value.items())
            elif isinstance(value, list):
                pending.extend(
                    (nested, f"{location}[{index}]") for index, nested in enumerate(value)
                )
    assert oidc_locations == [f"{ATTESTATION}.jobs.attest.permissions"]


def test_trusted_evidence_caller_chains_only_the_three_pinned_workflows():
    workflow, issues = load_document(ROOT, ROOT / TRUSTED_EVIDENCE_CALLER)
    assert issues == []
    prefix = "bodharma/zero-trust-workflows/.github/workflows/"
    assert workflow == {
        "name": "trusted-evidence",
        "on": {"push": {"branches": ["main"]}},
        "permissions": {"contents": "read"},
        "jobs": {
            "conformance": {"uses": f"{prefix}reusable-conformance.yml@{TRUSTED_EVIDENCE_SHA}"},
            "attest": {
                "needs": "conformance",
                "if": MAIN_GUARD,
                "uses": f"{prefix}reusable-evidence-attestation.yml@{TRUSTED_EVIDENCE_SHA}",
                "permissions": {"contents": "read", "id-token": "write"},
            },
            "verify": {
                "needs": "attest",
                "uses": f"{prefix}reusable-evidence-verification.yml@{TRUSTED_EVIDENCE_SHA}",
            },
        },
    }
    assert validate_workflow(workflow, TRUSTED_EVIDENCE_CALLER) == []
    assert re.findall(r"\b[0-9a-fA-F]{40}\b", (ROOT / TRUSTED_EVIDENCE_CALLER).read_text()) == [
        TRUSTED_EVIDENCE_SHA,
        TRUSTED_EVIDENCE_SHA,
        TRUSTED_EVIDENCE_SHA,
    ]


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
    release = re.search(r"^## 1\.0\.1\n(.*?)(?=^## |\Z)", changelog, re.MULTILINE | re.DOTALL)
    assert release is not None
    assert re.findall(r"Tested workflow SHA: `([0-9a-f]{40})`", release[1]) == [SUPPORTED_SHA]


def test_changelog_records_the_trusted_evidence_release_sha():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    release = re.search(r"^## 1\.1\.0\n(.*?)(?=^## |\Z)", changelog, re.MULTILINE | re.DOTALL)
    assert release is not None
    assert re.findall(r"Tested workflow SHA: `([0-9a-f]{40})`", release[1]) == [
        TRUSTED_EVIDENCE_SHA
    ]


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

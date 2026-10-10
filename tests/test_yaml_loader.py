import pytest
import yaml

from ztwf import validate


def test_workflow_keys_and_true_false_are_preserved(tmp_path):
    path = tmp_path / "workflow.yml"
    path.write_text("on: off\nyes: no\ntrue_value: true\nfalse_value: false\n")
    document, issues = validate.load_document(tmp_path, path)
    assert issues == []
    assert document == {"on": "off", "yes": "no", "true_value": True, "false_value": False}
    assert yaml.safe_load("on: off") == {True: False}


@pytest.mark.parametrize(
    "text",
    [
        "name: one\nname: two\n",
        "jobs:\n  check: {}\n  check: {}\n",
        "base: &base {name: one}\n<<: *base\nname: two\n",
    ],
)
def test_duplicate_keys_fail_with_a_path(tmp_path, text):
    path = tmp_path / "workflow.yml"
    path.write_text(text)
    document, issues = validate.load_document(tmp_path, path)
    assert document is None
    assert len(issues) == 1
    assert issues[0].startswith("workflow.yml: yaml: found duplicate key")


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("name: one\n---\nname: two\n", "expected exactly one document"),
        ("", "expected a mapping document"),
        ("null\n", "expected a mapping document"),
        ("[]\n", "expected a mapping document"),
        ("name: [\n", None),
        ("? [one, two]\n: value\n", None),
        ("!!python/object:builtins.object {}\n", None),
    ],
)
def test_bad_yaml_returns_issues(tmp_path, text, problem):
    path = tmp_path / ".github/workflows/check.yml"
    path.parent.mkdir(parents=True)
    path.write_text(text)
    assert validate.validate_repository(tmp_path)
    document, issues = validate.load_document(tmp_path, path)
    assert document is None
    assert len(issues) == 1
    prefix = ".github/workflows/check.yml: yaml: "
    assert issues[0].startswith(prefix)
    if problem:
        assert issues == [prefix + problem]


def test_recursive_alias_does_not_loop(tmp_path):
    path = tmp_path / ".github/workflows/check.yml"
    path.parent.mkdir(parents=True)
    path.write_text("name: check\non: push\npermissions: {}\njobs: {}\nloop: &loop [*loop]\n")
    assert validate.validate_repository(tmp_path) == [
        ".github/workflows/check.yml: jobs: expected a non-empty mapping"
    ]


def test_unreadable_document_returns_an_issue(tmp_path):
    document, issues = validate.load_document(tmp_path, tmp_path / "missing.yml")
    assert document is None
    assert issues[0].startswith("missing.yml: yaml: ")


def test_invalid_encoding_returns_an_issue(tmp_path):
    path = tmp_path / "workflow.yml"
    path.write_bytes(b"\xff")
    document, issues = validate.load_document(tmp_path, path)
    assert document is None
    assert issues[0].startswith("workflow.yml: yaml: ")

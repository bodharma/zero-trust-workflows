from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import ClassVar

import yaml

DOCUMENT_GLOBS = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "actions/**/action.yml",
    "actions/**/action.yaml",
)
EXTERNAL_REF = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.@-]+)*@[0-9a-fA-F]{40}$"
)
# Skip quoted literals while stopping at the enclosing expression boundary.
SECRET_EXPRESSION = re.compile(r"\$\{\{(?:'(?:[^']|'')*'|(?!\}\})[^'])*?\bsecrets\b", re.IGNORECASE)


class WorkflowLoader(yaml.SafeLoader):
    yaml_implicit_resolvers: ClassVar[dict] = {
        key: [(tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:bool"]
        for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                None, None, "expected a mapping node", node.start_mark
            )
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise yaml.constructor.ConstructorError(
                    None, None, "found unhashable key", key_node.start_mark
                ) from error
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    None, None, f"found duplicate key {key!r}", key_node.start_mark
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def load_document(root: Path, path: Path) -> tuple[dict[str, object] | None, list[str]]:
    """Return one mapping document or stable path-qualified issues."""
    location = f"{path.relative_to(root).as_posix()}: yaml"
    try:
        text = path.read_text(encoding="utf-8")
        documents = list(yaml.load_all(text, Loader=WorkflowLoader))
    except (yaml.YAMLError, OSError, ValueError) as error:
        return None, [f"{location}: {getattr(error, 'problem', None) or str(error)}"]
    if len(documents) > 1:
        return None, [f"{location}: expected exactly one document"]
    if not documents or not isinstance(documents[0], dict):
        return None, [f"{location}: expected a mapping document"]
    return documents[0], []


def validate_permissions(value: object, location: str) -> list[str]:
    if isinstance(value, dict) and value in ({}, {"contents": "read"}):
        return []
    return [f"{location}: expected {{}} or {{contents: read}}"]


def validate_uses(value: object, location: str) -> list[str]:
    if isinstance(value, str):
        if value.startswith("./") and ".." not in value.split("/"):
            return []
        if EXTERNAL_REF.fullmatch(value):
            return []
    return [f"{location}: expected a safe local path or a full 40-hex SHA"]


def validate_steps(value: object, location: str) -> list[str]:
    if not isinstance(value, list) or not value:
        return [f"{location}: expected a non-empty list"]
    issues = []
    for index, step in enumerate(value):
        step_location = f"{location}[{index}]"
        if not isinstance(step, dict):
            issues.append(f"{step_location}: expected a mapping step")
            continue
        if ("run" in step) == ("uses" in step):
            issues.append(f"{step_location}: expected exactly one of run or uses")
        if "uses" in step:
            issues.extend(validate_uses(step["uses"], f"{step_location}.uses"))
        if "run" in step and (not isinstance(step["run"], str) or not step["run"].strip()):
            issues.append(f"{step_location}.run: expected non-empty literal shell text")
    return sorted(issues)


def validate_workflow(document: dict[str, object], location: str) -> list[str]:
    issues = []
    if not isinstance(document.get("name"), str) or not document["name"].strip():
        issues.append(f"{location}: name: expected a non-empty string")
    triggers = document.get("on")
    if isinstance(triggers, str):
        triggers = [triggers]
    if (
        not isinstance(triggers, (dict, list))
        or not triggers
        or any(trigger not in ("workflow_call", "pull_request", "push") for trigger in triggers)
    ):
        issues.append(f"{location}: on: expected only workflow_call, pull_request, or push")
    issues.extend(validate_permissions(document.get("permissions"), f"{location}: permissions"))
    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        issues.append(f"{location}: jobs: expected a non-empty mapping")
        return sorted(issues)
    for name, job in jobs.items():
        job_location = f"{location}: jobs.{name}"
        if not isinstance(job, dict):
            issues.append(f"{job_location}: expected a mapping job")
            continue
        if "permissions" in job:
            issues.extend(validate_permissions(job["permissions"], f"{job_location}.permissions"))
        if "uses" in job:
            issues.extend(validate_uses(job["uses"], f"{job_location}.uses"))
            if set(job) - {"uses", "permissions"}:
                issues.append(f"{job_location}: caller jobs allow only uses and permissions")
            continue
        if job.get("runs-on") != "ubuntu-latest":
            issues.append(f"{job_location}.runs-on: expected ubuntu-latest")
        timeout = job.get("timeout-minutes")
        if type(timeout) is not int or not 1 <= timeout <= 30:
            issues.append(f"{job_location}.timeout-minutes: expected an integer from 1 through 30")
        issues.extend(validate_steps(job.get("steps"), f"{job_location}.steps"))
    return sorted(issues)


def validate_action(document: dict[str, object], location: str) -> list[str]:
    runs = document.get("runs")
    if not isinstance(runs, dict):
        return [f"{location}: runs: expected a mapping"]
    issues = []
    if runs.get("using") != "composite":
        issues.append(f"{location}: runs.using: expected composite")
    issues.extend(validate_steps(runs.get("steps"), f"{location}: runs.steps"))
    return sorted(issues)


def discover_documents(root: Path) -> list[Path]:
    return sorted({path for pattern in DOCUMENT_GLOBS for path in root.glob(pattern)})


def validate_repository(root: Path) -> list[str]:
    documents = discover_documents(root)
    if not documents:
        return ["repository: no workflow or composite-action documents found"]
    issues = []
    for path in documents:
        document, errors = load_document(root, path)
        issues.extend(errors)
        if document is None:
            continue
        location = path.relative_to(root).as_posix()
        validator = (
            validate_workflow if location.startswith(".github/workflows/") else validate_action
        )
        issues.extend(validator(document, location))
        pending = [(document, f"{location}:")]
        visited = set()
        while pending:
            value, value_location = pending.pop()
            if isinstance(value, (dict, list)):
                if id(value) in visited:
                    continue
                visited.add(id(value))
            if isinstance(value, dict):
                for key, nested in value.items():
                    nested_location = (
                        f"{value_location} {key}"
                        if value_location.endswith(":")
                        else f"{value_location}.{key}"
                    )
                    if key == "secrets":
                        issues.append(f"{nested_location}: secrets are forbidden")
                    if isinstance(key, str) and SECRET_EXPRESSION.search(key):
                        issues.append(f"{nested_location}: secret expressions are forbidden")
                    if key == "run" and isinstance(nested, str) and "${{" in nested:
                        issues.append(f"{nested_location}: shell expressions are forbidden")
                    pending.append((nested, nested_location))
            elif isinstance(value, list):
                pending.extend(
                    (nested, f"{value_location}[{index}]") for index, nested in enumerate(value)
                )
            elif isinstance(value, str) and SECRET_EXPRESSION.search(value):
                issues.append(f"{value_location}: secret expressions are forbidden")
    return sorted(issues)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    issues = validate_repository(parser.parse_args().root)
    for issue in issues:
        print(issue)
    return 1 if issues else 0

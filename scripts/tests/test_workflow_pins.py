"""Supply-chain pin check: every action is pinned to a full commit SHA with a version comment,
and every service/container image is pinned by digest. Run with pytest or unittest.

Known limits (line-based regexes, no YAML parser): string-form `container: <image>` and flow-style
`- { uses: ... }` are not checked, and neither is used in this repo; keep to block style. The version
comment is not checked against the SHA (that needs the network)."""
import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
IMAGE = re.compile(r"^\s*(?:-\s+)?image:\s*(?P<ref>\S+)")
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^\s*#\s*v\d+(\.\d+)*\b")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")


def workflow_files():
    return sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))


def problems(files):
    out = []
    for f in files:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            m = USES.match(line)
            if m:
                ref = m["ref"].strip("'\"")
                if ref.startswith("./"):
                    continue  # local action or reusable workflow in this repo
                if not PINNED.match(ref):
                    out.append(f"{f.name}:{n}: uses not pinned to a 40-hex SHA: {ref}")
                elif not VERSION_COMMENT.match(m["rest"]):
                    out.append(f"{f.name}:{n}: uses lacks a '# vX.Y.Z' comment: {ref}")
            m = IMAGE.match(line)
            if m:
                ref = m["ref"].strip("'\"")
                if not DIGEST.search(ref):
                    out.append(f"{f.name}:{n}: image not pinned by @sha256 digest: {ref}")
    return out


class WorkflowPins(unittest.TestCase):
    def test_workflows_exist(self):
        self.assertTrue(workflow_files())

    def test_all_pinned(self):
        self.assertEqual(problems(workflow_files()), [])

    def test_checker_catches_bad_pins(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.yml"
            f.write_text("steps:\n  - uses: actions/checkout@v4\n"
                         f"  - uses: actions/cache@{'a' * 40}\n"
                         "services:\n  db:\n    image: postgres:16\n")
            self.assertEqual(len(problems([f])), 3)


if __name__ == "__main__":
    unittest.main()

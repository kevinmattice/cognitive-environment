import unittest
from pathlib import Path

from workspace_runtime.errors import SourceError
from workspace_runtime.runtime import WorkspaceRuntime


class WorkspaceRuntimeTests(unittest.TestCase):
    def test_list_finds_example_workspace(self) -> None:
        rt = WorkspaceRuntime(Path("workspaces"))
        items = rt.list_workspaces()
        ids = {w.workspace_id for w in items}
        self.assertIn("example-workspace", ids)

    def test_open_sources_and_read(self) -> None:
        rt = WorkspaceRuntime(Path("workspaces"))
        rt.open("example-workspace")

        srcs = {s.source_id: s for s in rt.sources()}
        self.assertIn("readme", srcs)
        self.assertTrue(srcs["readme"].exists)
        self.assertTrue(srcs["readme"].supported_type)

        content = rt.read_source("readme")
        self.assertIn("Example Source", content)

    def test_reject_undeclared_source(self) -> None:
        rt = WorkspaceRuntime(Path("workspaces"))
        rt.open("example-workspace")
        with self.assertRaises(SourceError):
            rt.read_source("nope")

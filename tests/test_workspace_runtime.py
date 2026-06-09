import unittest
import tempfile
from pathlib import Path

from workspace_runtime.errors import SourceError
from workspace_runtime.runtime import WorkspaceRuntime
from workspace_runtime.manifest import load_manifest


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

    def test_manifest_source_metadata_is_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws_dir = Path(tmp) / "meta-workspace"
            ws_dir.mkdir()
            (ws_dir / "workspace.toml").write_text(
                "\n".join(
                    [
                        'workspace_id = "meta-workspace"',
                        'title = "Meta Workspace"',
                        "",
                        "[[sources]]",
                        'source_id = "aa_trip_confirmation"',
                        'path = "sources/AA trip confirmation CHA—MSO.pdf"',
                        'display_name = "AA Trip Confirmation"',
                        'kind = "pdf"',
                        'category = "flight"',
                        'keywords = ["flight", "dfw"]',
                        'aliases = ["aa confirmation"]',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            manifest = load_manifest(ws_dir / "workspace.toml")

        src = manifest.sources[0]
        self.assertEqual(src.display_name, "AA Trip Confirmation")
        self.assertEqual(src.category, "flight")
        self.assertEqual(src.keywords, ("flight", "dfw"))
        self.assertEqual(src.aliases, ("aa confirmation",))

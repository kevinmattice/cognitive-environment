import tempfile
import unittest
from pathlib import Path

from workspace_runtime.errors import SourceError
from workspace_runtime.runtime import WorkspaceRuntime


def _pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _build_simple_pdf_bytes(page_texts: list[str]) -> bytes:
    # Minimal deterministic PDF with a single built-in Type1 font (Helvetica) and
    # one content stream per page. This is intentionally tiny and avoids adding
    # any dependencies for test fixture generation.
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    objects: list[bytes] = []

    # 1: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    # 2: Pages (filled after page objects are assigned ids)
    objects.append(b"")  # placeholder

    # 3: Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_ids: list[int] = []
    content_obj_ids: list[int] = []

    next_id = 4
    for text in page_texts:
        content_id = next_id
        page_id = next_id + 1
        next_id += 2
        content_obj_ids.append(content_id)
        page_obj_ids.append(page_id)

        if text.strip():
            escaped = _pdf_escape(text)
            stream_body = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET\n".encode("ascii")
        else:
            stream_body = b"\n"

        stream_obj = b"<< /Length %d >>\nstream\n%sendstream" % (len(stream_body), stream_body)
        objects.append(stream_obj)  # content stream object

        page_obj = (
            b"<< /Type /Page /Parent 2 0 R "
            b"/Resources << /Font << /F1 3 0 R >> >> "
            b"/MediaBox [0 0 612 792] "
            + f"/Contents {content_id} 0 R".encode("ascii")
            + b" >>"
        )
        objects.append(page_obj)

    kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids).encode("ascii")
    pages_obj = b"<< /Type /Pages /Kids [ " + kids + b" ] /Count " + str(len(page_obj_ids)).encode("ascii") + b" >>"
    objects[1] = pages_obj

    out = bytearray()
    out += header
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("ascii")
        out += obj
        out += b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(offsets)}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode("ascii")
    out += b"trailer\n"
    out += b"<< /Size " + str(len(offsets)).encode("ascii") + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_at).encode("ascii") + b"\n%%EOF\n"
    return bytes(out)


class PdfSourceSupportTests(unittest.TestCase):
    def test_declared_pdf_is_supported_and_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = Path(tmp) / "workspaces"
            ws_dir = workspaces_dir / "pdf-ws"
            (ws_dir / "sources").mkdir(parents=True)
            (ws_dir / "workspace.toml").write_text(
                "\n".join(
                    [
                        'workspace_id = "pdf-ws"',
                        'title = "PDF Workspace"',
                        "",
                        "[[sources]]",
                        'source_id = "doc"',
                        'path = "sources/doc.pdf"',
                        "",
                        "[policies]",
                        "max_read_bytes = 8192",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws_dir / "sources" / "doc.pdf").write_bytes(_build_simple_pdf_bytes(["Hello PDF", "Second page"]))

            rt = WorkspaceRuntime(workspaces_dir)
            rt.open("pdf-ws")
            srcs = {s.source_id: s for s in rt.sources()}
            self.assertTrue(srcs["doc"].exists)
            self.assertTrue(srcs["doc"].supported_type)

            text = rt.read_source("doc")
            self.assertIn("--- page 1 ---", text)
            self.assertIn("--- page 2 ---", text)
            self.assertIn("Hello PDF", text)
            self.assertIn("Second page", text)

    def test_undeclared_pdf_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = Path(tmp) / "workspaces"
            ws_dir = workspaces_dir / "pdf-ws"
            (ws_dir / "sources").mkdir(parents=True)
            (ws_dir / "workspace.toml").write_text(
                "\n".join(
                    [
                        'workspace_id = "pdf-ws"',
                        'title = "PDF Workspace"',
                        "",
                        "[[sources]]",
                        'source_id = "doc"',
                        'path = "sources/doc.pdf"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws_dir / "sources" / "doc.pdf").write_bytes(_build_simple_pdf_bytes(["Hello"]))

            rt = WorkspaceRuntime(workspaces_dir)
            rt.open("pdf-ws")
            with self.assertRaises(SourceError):
                rt.read_source("not-declared")

    def test_pdf_path_traversal_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = Path(tmp) / "workspaces"
            ws_dir = workspaces_dir / "pdf-ws"
            ws_dir.mkdir(parents=True)
            (ws_dir / "workspace.toml").write_text(
                "\n".join(
                    [
                        'workspace_id = "pdf-ws"',
                        'title = "PDF Workspace"',
                        "",
                        "[[sources]]",
                        'source_id = "evil"',
                        'path = "../evil.pdf"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            rt = WorkspaceRuntime(workspaces_dir)
            rt.open("pdf-ws")
            with self.assertRaises(SourceError):
                rt.sources()

    def test_pdf_no_text_returns_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = Path(tmp) / "workspaces"
            ws_dir = workspaces_dir / "pdf-ws"
            (ws_dir / "sources").mkdir(parents=True)
            (ws_dir / "workspace.toml").write_text(
                "\n".join(
                    [
                        'workspace_id = "pdf-ws"',
                        'title = "PDF Workspace"',
                        "",
                        "[[sources]]",
                        'source_id = "doc"',
                        'path = "sources/doc.pdf"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws_dir / "sources" / "doc.pdf").write_bytes(_build_simple_pdf_bytes(["", "   "]))

            rt = WorkspaceRuntime(workspaces_dir)
            rt.open("pdf-ws")
            text = rt.read_source("doc")
            self.assertIn("PDF text extraction produced no text", text)

    def test_max_read_bytes_enforced_for_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = Path(tmp) / "workspaces"
            ws_dir = workspaces_dir / "pdf-ws"
            (ws_dir / "sources").mkdir(parents=True)
            (ws_dir / "workspace.toml").write_text(
                "\n".join(
                    [
                        'workspace_id = "pdf-ws"',
                        'title = "PDF Workspace"',
                        "",
                        "[[sources]]",
                        'source_id = "doc"',
                        'path = "sources/doc.pdf"',
                        "",
                        "[policies]",
                        "max_read_bytes = 200",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws_dir / "sources" / "doc.pdf").write_bytes(_build_simple_pdf_bytes(["Hello PDF"]))

            rt = WorkspaceRuntime(workspaces_dir)
            rt.open("pdf-ws")
            text = rt.read_source("doc")
            self.assertTrue(text)
            self.assertLessEqual(len(text.encode("utf-8")), 200)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workspace_runtime.errors import SourceError, WorkspaceError
from workspace_runtime.manifest import WorkspaceManifest, find_manifest_path, load_manifest
from workspace_runtime.pdf_reader import PdfTextExtractionError, extract_pdf_text


SUPPORTED_READ_EXTENSIONS = {".md", ".txt", ".pdf"}


@dataclass(frozen=True)
class WorkspaceInfo:
    workspace_id: str
    title: str
    path: Path


@dataclass(frozen=True)
class SourceInfo:
    source_id: str
    rel_path: str
    abs_path: Path
    exists: bool
    supported_type: bool
    display_name: str | None = None
    kind: str | None = None
    category: str | None = None
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


class WorkspaceRuntime:
    def __init__(self, workspaces_dir: Path) -> None:
        self.workspaces_dir = workspaces_dir
        self._active: WorkspaceManifest | None = None
        self._active_dir: Path | None = None

    @property
    def active_workspace_id(self) -> str | None:
        return self._active.workspace_id if self._active else None

    def status_line(self) -> str:
        if not self._active:
            return "not configured"
        return f"open ({self._active.workspace_id})"

    def list_workspaces(self) -> list[WorkspaceInfo]:
        results: list[WorkspaceInfo] = []
        if not self.workspaces_dir.exists():
            return results
        if not self.workspaces_dir.is_dir():
            raise WorkspaceError(f"workspaces_dir is not a directory: {self.workspaces_dir}")

        for child in sorted(self.workspaces_dir.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            manifest_path = find_manifest_path(child)
            if not manifest_path:
                continue
            manifest = load_manifest(manifest_path)
            results.append(WorkspaceInfo(workspace_id=manifest.workspace_id, title=manifest.title, path=child))
        return results

    def open(self, workspace_id: str) -> WorkspaceManifest:
        for ws in self.list_workspaces():
            if ws.workspace_id == workspace_id:
                manifest_path = find_manifest_path(ws.path)
                assert manifest_path is not None
                manifest = load_manifest(manifest_path)
                self._active = manifest
                self._active_dir = ws.path
                return manifest
        raise WorkspaceError(f"workspace not found: {workspace_id}")

    def active_manifest(self) -> WorkspaceManifest:
        if not self._active or not self._active_dir:
            raise WorkspaceError("no active workspace; use: workspace open <id>")
        return self._active

    def sources(self) -> list[SourceInfo]:
        manifest = self.active_manifest()
        base = self._active_dir
        assert base is not None
        infos: list[SourceInfo] = []
        for decl in manifest.sources:
            abs_path = self._resolve_declared_path(base, decl.path)
            exists = abs_path.is_file()
            supported = abs_path.suffix.lower() in SUPPORTED_READ_EXTENSIONS
            infos.append(
                SourceInfo(
                    source_id=decl.source_id,
                    rel_path=decl.path,
                    abs_path=abs_path,
                    exists=exists,
                    supported_type=supported,
                    display_name=decl.display_name,
                    kind=decl.kind,
                    category=decl.category,
                    keywords=decl.keywords,
                    aliases=decl.aliases,
                )
            )
        return infos

    def read_source(self, source_id: str) -> str:
        manifest = self.active_manifest()
        base = self._active_dir
        assert base is not None

        decl = next((s for s in manifest.sources if s.source_id == source_id), None)
        if decl is None:
            raise SourceError(f"source not declared: {source_id}")

        abs_path = self._resolve_declared_path(base, decl.path)
        if not abs_path.exists():
            raise SourceError(f"source missing: {source_id} -> {decl.path}")
        if not abs_path.is_file():
            raise SourceError(f"source is not a file: {source_id} -> {decl.path}")

        ext = abs_path.suffix.lower()
        if ext not in SUPPORTED_READ_EXTENSIONS:
            raise SourceError(f"unsupported source type: {source_id} -> {decl.path} ({ext})")

        data = abs_path.read_bytes()
        # Preserve existing behavior for plain text sources: refuse to read files
        # that exceed max_read_bytes. For PDFs, max_read_bytes is applied to the
        # extracted text output (see below) rather than the raw PDF file size.
        if ext != ".pdf" and len(data) > manifest.policies.max_read_bytes:
            raise SourceError(
                f"source too large: {source_id} ({len(data)} bytes > max_read_bytes {manifest.policies.max_read_bytes})"
            )

        if ext == ".pdf":
            try:
                extracted = extract_pdf_text(data, max_output_bytes=manifest.policies.max_read_bytes)
            except PdfTextExtractionError as exc:
                raise SourceError(f"PDF read failed: {source_id} -> {decl.path}: {exc}") from exc

            if not extracted.had_any_text:
                return "PDF text extraction produced no text; OCR is not supported.\n"
            return extracted.text

        return data.decode("utf-8", errors="replace")

    def _resolve_declared_path(self, base: Path, rel_path: str) -> Path:
        # Reject absolute paths and path traversal. Everything must live under the workspace dir.
        candidate = Path(rel_path)
        if candidate.is_absolute():
            raise SourceError(f"undeclared path rejected (absolute): {rel_path}")
        joined = (base / candidate).resolve()
        base_resolved = base.resolve()
        if base_resolved not in joined.parents and joined != base_resolved:
            raise SourceError(f"undeclared path rejected (outside workspace): {rel_path}")
        return joined

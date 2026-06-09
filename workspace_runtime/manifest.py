from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

from workspace_runtime.errors import ManifestError


SUPPORTED_MANIFEST_FILENAMES = ("workspace.toml",)


@dataclass(frozen=True)
class SourceDecl:
    source_id: str
    path: str
    display_name: str | None = None
    kind: str | None = None
    category: str | None = None
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Intent:
    domains: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()


@dataclass(frozen=True)
class Policies:
    max_read_bytes: int = 8192


@dataclass(frozen=True)
class WorkspaceManifest:
    workspace_id: str
    title: str
    description: str | None
    notes: str | None
    sources: tuple[SourceDecl, ...]
    policies: Policies
    intent: Intent | None = None


def _require_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"manifest missing or invalid {key}")
    return value.strip()


def _optional_str(obj: dict[str, Any], key: str) -> str | None:
    value = obj.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ManifestError(f"manifest invalid {key} (expected string)")
    value = value.strip()
    return value if value else None


def _optional_str_list(obj: dict[str, Any], key: str) -> tuple[str, ...]:
    value = obj.get(key)
    if value is None:
        return tuple()
    if not isinstance(value, list):
        raise ManifestError(f"manifest invalid {key} (expected list of strings)")

    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ManifestError(f"manifest invalid {key} (expected list of strings)")
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return tuple(items)


def _parse_sources(raw: Any) -> tuple[SourceDecl, ...]:
    if raw is None:
        return tuple()
    if not isinstance(raw, list):
        raise ManifestError("manifest sources must be a list")

    sources: list[SourceDecl] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ManifestError("manifest sources entries must be objects")
        source_id = item.get("source_id")
        path = item.get("path")
        display_name = item.get("display_name")
        kind = item.get("kind")
        category = item.get("category")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ManifestError("manifest sources entry missing source_id")
        if not isinstance(path, str) or not path.strip():
            raise ManifestError(f"manifest sources entry {source_id!r} missing path")
        if display_name is not None and (not isinstance(display_name, str) or not display_name.strip()):
            raise ManifestError(f"manifest sources entry {source_id!r} invalid display_name")
        if kind is not None and (not isinstance(kind, str) or not kind.strip()):
            raise ManifestError(f"manifest sources entry {source_id!r} invalid kind")
        if category is not None and (not isinstance(category, str) or not category.strip()):
            raise ManifestError(f"manifest sources entry {source_id!r} invalid category")
        source_id = source_id.strip()
        if source_id in seen:
            raise ManifestError(f"duplicate source_id in manifest: {source_id}")
        seen.add(source_id)
        sources.append(
            SourceDecl(
                source_id=source_id,
                path=path.strip(),
                display_name=display_name.strip() if isinstance(display_name, str) else None,
                kind=kind.strip() if isinstance(kind, str) else None,
                category=category.strip() if isinstance(category, str) else None,
                keywords=_optional_str_list(item, "keywords"),
                aliases=_optional_str_list(item, "aliases"),
            )
        )
    return tuple(sources)


def _parse_policies(raw: Any) -> Policies:
    if raw is None:
        return Policies()
    if not isinstance(raw, dict):
        raise ManifestError("manifest policies must be an object")
    max_read_bytes = raw.get("max_read_bytes", 8192)
    if not isinstance(max_read_bytes, int) or max_read_bytes <= 0 or max_read_bytes > 1024 * 1024:
        raise ManifestError("manifest policies.max_read_bytes must be a positive int <= 1048576")
    return Policies(max_read_bytes=max_read_bytes)


def _parse_intent(raw: Any) -> Intent | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ManifestError("manifest intent must be an object")
    return Intent(
        domains=_optional_str_list(raw, "domains"),
        keywords=_optional_str_list(raw, "keywords"),
        entities=_optional_str_list(raw, "entities"),
    )


def load_manifest(manifest_path: Path) -> WorkspaceManifest:
    try:
        data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"manifest not found: {manifest_path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"manifest invalid TOML: {manifest_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("manifest root must be an object")

    workspace_id = _require_str(data, "workspace_id")
    title = _require_str(data, "title")
    description = _optional_str(data, "description")
    notes = _optional_str(data, "notes")
    sources = _parse_sources(data.get("sources"))
    policies = _parse_policies(data.get("policies"))
    intent = _parse_intent(data.get("intent"))

    return WorkspaceManifest(
        workspace_id=workspace_id,
        title=title,
        description=description,
        notes=notes,
        sources=sources,
        policies=policies,
        intent=intent,
    )


def find_manifest_path(workspace_dir: Path) -> Path | None:
    for name in SUPPORTED_MANIFEST_FILENAMES:
        candidate = workspace_dir / name
        if candidate.is_file():
            return candidate
    return None

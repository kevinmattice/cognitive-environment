from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from models.interface import LocalModel, ModelRequest
from workspace_runtime.errors import WorkspaceError
from workspace_runtime.manifest import Intent
from workspace_runtime.runtime import SourceInfo, WorkspaceRuntime


QUESTION_DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "travel": (
        "flight",
        "airport",
        "airline",
        "layover",
        "connection",
        "boarding",
        "gate",
        "departure",
        "arrival",
        "return",
        "outbound",
        "inbound",
        "leave",
        "arrive",
    ),
    "itinerary": (
        "itinerary",
        "schedule",
        "timeline",
        "trip",
        "plan",
        "when",
        "leave",
        "return",
        "outbound",
        "inbound",
    ),
    "logistics": (
        "fragile",
        "risk",
        "risky",
        "backup",
        "contingency",
        "delay",
        "cancel",
        "cancellation",
        "weather",
        "transport",
        "lodging",
        "hotel",
        "insurance",
        "trip",
        "plan",
    ),
}

SOURCE_DOMAIN_AFFINITY: dict[str, dict[str, int]] = {
    "travel": {"flight": 3, "itinerary": 2, "trip": 1},
    "itinerary": {"itinerary": 3, "trip": 2, "flight": 2, "plan": 1, "document": 1},
    "logistics": {"contingency": 4, "plan": 3, "flight": 2, "itinerary": 2, "lodging": 2, "insurance": 2, "trip": 1},
}


@dataclass(frozen=True)
class AskConfig:
    provider: str
    model_name: str
    max_context_bytes: int
    timeout_s: int


@dataclass(frozen=True)
class ContextBuildResult:
    ok: bool
    context_text: str
    sources_used: tuple[str, ...]
    truncated: bool
    error: str | None = None


@dataclass(frozen=True)
class SourceSelectionResult:
    selected_sources: tuple[SourceInfo, ...]
    footer: str | None
    clarification: str | None = None


def _readable_existing_sources(workspace: WorkspaceRuntime) -> list[SourceInfo]:
    sources = workspace.sources()
    readable = [s for s in sources if s.exists and s.supported_type]
    return sorted(readable, key=lambda s: s.source_id)


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _tokenize_for_match(text: str) -> set[str]:
    normalized = _normalize_for_match(text)
    if not normalized:
        return set()
    return {token for token in normalized.split() if token}


def _text_metadata_value(source: SourceInfo, attr: str) -> str | None:
    value = getattr(source, attr, None)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value else None


def _iter_text_metadata_values(source: SourceInfo, attr: str) -> tuple[str, ...]:
    value = getattr(source, attr, ())
    if not isinstance(value, (list, tuple)):
        return tuple()
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return tuple(items)


def _phrase_matches(normalized_question: str, question_tokens: set[str], phrase: str) -> bool:
    normalized_phrase = _normalize_for_match(phrase)
    if not normalized_phrase:
        return False
    if " " in normalized_phrase:
        return normalized_phrase in normalized_question
    return normalized_phrase in question_tokens


def _score_source(question_norm: str, question_tokens: set[str], source: SourceInfo) -> int:
    score = 0

    category = _text_metadata_value(source, "category")
    if category and _phrase_matches(question_norm, question_tokens, category):
        score += 2

    aliases = _iter_text_metadata_values(source, "aliases")
    for alias in aliases:
        if _phrase_matches(question_norm, question_tokens, alias):
            score += 4

    keywords = _iter_text_metadata_values(source, "keywords")
    for keyword in keywords:
        if _phrase_matches(question_norm, question_tokens, keyword):
            score += 1

    return score


def _format_selection_footer(selected_sources: list[SourceInfo]) -> str:
    labels: list[str] = []
    seen: set[str] = set()
    for src in selected_sources:
        label = _source_display_label(src)
        if label in seen:
            continue
        seen.add(label)
        labels.append(f"- {label}")
    return "\n".join(labels)


def _source_display_label(source: SourceInfo) -> str:
    display_name = _text_metadata_value(source, "display_name")
    if display_name:
        return display_name
    return Path(source.rel_path).name or source.source_id


def _source_clarification_label(source: SourceInfo, duplicate_labels: set[str]) -> str:
    label = _source_display_label(source)
    if label in duplicate_labels:
        return f"{label} ({source.source_id})"
    return label


def _build_clarification(selected_sources: list[SourceInfo]) -> str:
    if not selected_sources:
        return "I think this is in your workspace documents, but I need a little more direction before I pick a source."

    counts: dict[str, int] = {}
    for src in selected_sources:
        label = _source_display_label(src)
        counts[label] = counts.get(label, 0) + 1
    duplicate_labels = {label for label, count in counts.items() if count > 1}
    labels = [_source_clarification_label(src, duplicate_labels) for src in selected_sources]

    if len(labels) == 1:
        return f"I think this is in your workspace documents. Should I use {labels[0]}?"
    if len(labels) == 2:
        return (
            "I think this is in your workspace documents, but I'm not sure which one to trust for this specific detail. "
            f"Should I use {labels[0]} or {labels[1]}?"
        )
    options = "\n".join(f"- {label}" for label in labels[:3])
    return (
        "I think this is in your workspace documents, but I'm not sure which one to trust for this specific detail. "
        "Which of these should I use?\n"
        f"{options}"
    )


def _collapse_adjacent_duplicate_words(text: str) -> str:
    pattern = re.compile(r"\b([A-Za-z][A-Za-z']*)\b(?:\s+\1\b)+", re.IGNORECASE)
    previous = None
    current = text
    while current != previous:
        previous = current
        current = pattern.sub(r"\1", current)
    return current


def _normalize_wrapped_artifacts(text: str) -> str:
    current = text
    previous = None
    while current != previous:
        previous = current
        current = re.sub(r"^<([^<>\n]+)>$", r"\1", current.strip())
        current = re.sub(r"<([^<>\n]+)>", r"\1", current)
        current = re.sub(r"\b(\d{1,2}:\d{2})\s+\1\s*(AM|PM)\b", r"\1 \2", current)
        current = re.sub(r"\b(\d{1,2})\s+\1:(\d{2}\b)", r"\1:\2", current)
        current = re.sub(r"\b(\d+)\s+(hour|hours)\s+\d\s+(\d{2})\s+(minute|minutes)\b", r"\1 \2 \3 \4", current, flags=re.IGNORECASE)
        current = re.sub(r"\b(\d+)-\s+\1-(minute|minutes|hour|hours)\b", r"\1-\2", current, flags=re.IGNORECASE)
        current = re.sub(r"\b([A-Z])\s+(\1[A-Z0-9]{4,})\b", r"\2", current)
        current = re.sub(r"\b([a-z])\s+(\1[a-z]{2,})\b", r"\2", current)
        current = re.sub(r"\b([A-Za-z]{3,})\s+(\1[A-Za-z]+)\b", r"\2", current)
        current = _collapse_adjacent_duplicate_words(current)
    return current


def _cleanup_model_answer(text: str) -> str:
    lines = [line.rstrip() for line in (text or "").splitlines()]
    cleaned_lines: list[str] = []
    paragraph_parts: list[str] = []
    bullet_prefix: str | None = None

    def flush_paragraph() -> None:
        nonlocal bullet_prefix
        if paragraph_parts:
            paragraph = " ".join(part.strip() for part in paragraph_parts if part.strip())
            paragraph = re.sub(r"\s+", " ", paragraph).strip()
            paragraph = re.sub(r"\b(\d{1,2}:)\s+(\d{1,2}:\d{2}\b)", r"\2", paragraph)
            paragraph = _normalize_wrapped_artifacts(paragraph)
            if paragraph:
                if bullet_prefix:
                    cleaned_lines.append(f"{bullet_prefix}{paragraph}")
                else:
                    cleaned_lines.append(paragraph)
            paragraph_parts.clear()
            bullet_prefix = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            flush_paragraph()
            bullet_prefix = stripped[:2]
            paragraph_parts.append(stripped[2:].strip())
            continue
        paragraph_parts.append(stripped)

    flush_paragraph()
    return "\n".join(cleaned_lines).strip()

def _question_likely_single_fact(question_norm: str, question_tokens: set[str]) -> bool:
    if not question_norm:
        return False
    single_fact_starts = (
        "when ",
        "what ",
        "where ",
        "who ",
        "which ",
        "how much",
        "how many",
        "how long",
        "what time",
    )
    if not question_norm.startswith(single_fact_starts):
        return False
    multi_source_cues = (
        " and ",
        " or ",
        " both ",
        " while ",
        " before ",
        " after ",
        " make ",
        " plus ",
        " then ",
    )
    if any(cue in f" {question_norm} " for cue in multi_source_cues):
        return False
    if {"lodge", "flight"}.issubset(question_tokens):
        return False
    return True


def _question_prefers_itemized_answer(question_norm: str, question_tokens: set[str]) -> bool:
    if not question_norm:
        return False
    if any(token in question_tokens for token in {"all", "every", "list", "times", "time", "flights", "legs"}):
        if any(phrase in question_norm for phrase in ("departure times", "flight", "flights", "depart", "leave")):
            return True
    return False


def _question_prefers_multi_source_review(question_norm: str, question_tokens: set[str]) -> bool:
    if not question_norm:
        return False
    if any(token in question_tokens for token in {"fragile", "risk", "risks", "risky", "backup", "contingency"}):
        return True
    return "trip plan" in question_norm or "look fragile" in question_norm


def _select_declared_sources(question: str, readable: list[SourceInfo]) -> list[SourceInfo] | None:
    q = question.strip()
    if not q:
        return None

    by_id = {s.source_id: s for s in readable}
    by_path = {s.rel_path: s for s in readable}

    hits: list[SourceInfo] = []
    for source_id, src in by_id.items():
        if re.search(rf"\b{re.escape(source_id)}\b", q):
            hits.append(src)

    for rel_path, src in by_path.items():
        if rel_path in q:
            hits.append(src)

    if not hits:
        return None

    unique = {s.source_id: s for s in hits}
    return sorted(unique.values(), key=lambda s: s.source_id)


def _select_strong_librarian_sources(question: str, readable: list[SourceInfo]) -> SourceSelectionResult | None:
    question_norm = _normalize_for_match(question)
    question_tokens = _tokenize_for_match(question)
    scored: list[tuple[int, SourceInfo]] = []

    for src in readable:
        score = _score_source(question_norm, question_tokens, src)
        if score > 0:
            scored.append((score, src))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], item[1].source_id))
    top_score = scored[0][0]
    second_score = scored[1][0] if len(scored) > 1 else None

    if len(scored) > 1 and second_score == top_score and _question_likely_single_fact(question_norm, question_tokens):
        return SourceSelectionResult(selected_sources=tuple(), footer=None, clarification=_build_clarification([src for _, src in scored[:3]]))

    selected = [src for score, src in scored if score >= 2][:3]
    if not selected:
        selected = [scored[0][1]]

    footer = _format_selection_footer(selected)
    return SourceSelectionResult(selected_sources=tuple(selected), footer=footer)


def _normalized_intent_domains(intent: Intent) -> tuple[str, ...]:
    domains: list[str] = []
    for domain in intent.domains:
        normalized = _normalize_for_match(domain)
        if normalized and normalized not in domains:
            domains.append(normalized)
    return tuple(domains)


def _match_any_terms(question_norm: str, question_tokens: set[str], terms: tuple[str, ...]) -> int:
    hits = 0
    for term in terms:
        if _phrase_matches(question_norm, question_tokens, term):
            hits += 1
    return hits

def _analyze_workspace_intent(question: str, intent: Intent | None) -> tuple[bool, dict[str, int]]:
    if not isinstance(intent, Intent):
        return False, {}

    question_norm = _normalize_for_match(question)
    question_tokens = _tokenize_for_match(question)
    if not question_norm:
        return False, {}

    keyword_hits = _match_any_terms(question_norm, question_tokens, intent.keywords)
    entity_hits = _match_any_terms(question_norm, question_tokens, intent.entities)

    domain_signals: dict[str, int] = {}
    for domain in _normalized_intent_domains(intent):
        signal = 0
        if _phrase_matches(question_norm, question_tokens, domain):
            signal += 1
        hint_hits = 0
        for hint in QUESTION_DOMAIN_HINTS.get(domain, ()): 
            if _phrase_matches(question_norm, question_tokens, hint):
                hint_hits += 1
        signal += min(hint_hits, 2)
        if signal > 0:
            domain_signals[domain] = signal

    relevance_score = (keyword_hits * 2) + (entity_hits * 3) + sum(domain_signals.values())
    relevant = relevance_score > 0
    if relevant and not domain_signals:
        for domain in _normalized_intent_domains(intent):
            domain_signals[domain] = 1

    return relevant, domain_signals


def _source_affinity_for_domain(source: SourceInfo, domain: str) -> int:
    affinities = SOURCE_DOMAIN_AFFINITY.get(domain, {})
    category = _normalize_for_match(_text_metadata_value(source, "category") or "")
    kind = _normalize_for_match(_text_metadata_value(source, "kind") or "")
    return max(affinities.get(category, 0), affinities.get(kind, 0))


def _score_likely_workspace_source(
    question_norm: str,
    question_tokens: set[str],
    source: SourceInfo,
    domain_signals: dict[str, int],
) -> int:
    score = _score_source(question_norm, question_tokens, source)
    best_affinity = 0
    for domain, signal in domain_signals.items():
        affinity = _source_affinity_for_domain(source, domain)
        if affinity:
            best_affinity = max(best_affinity, signal * affinity)
    return score + best_affinity


def _select_workspace_relevant_sources(question: str, readable: list[SourceInfo], intent: Intent | None) -> SourceSelectionResult | None:
    relevant, domain_signals = _analyze_workspace_intent(question, intent)
    if not relevant:
        return None

    question_norm = _normalize_for_match(question)
    question_tokens = _tokenize_for_match(question)
    scored: list[tuple[int, SourceInfo]] = []
    for src in readable:
        score = _score_likely_workspace_source(question_norm, question_tokens, src, domain_signals)
        if score > 0:
            scored.append((score, src))

    if not scored:
        return SourceSelectionResult(selected_sources=tuple(), footer=None, clarification=_build_clarification(readable[:3]))

    scored.sort(key=lambda item: (-item[0], item[1].source_id))
    top_score = scored[0][0]
    second_score = scored[1][0] if len(scored) > 1 else None
    single_fact = _question_likely_single_fact(question_norm, question_tokens)
    multi_review = _question_prefers_multi_source_review(question_norm, question_tokens)

    if single_fact and not multi_review and second_score is not None and top_score == second_score:
        return SourceSelectionResult(selected_sources=tuple(), footer=None, clarification=_build_clarification([src for _, src in scored[:3]]))

    if multi_review:
        selected = [src for _, src in scored[:3]]
    elif single_fact:
        selected = [scored[0][1]]
    else:
        selected = [src for score, src in scored if score >= max(2, top_score - 1)][:3]
        if not selected:
            selected = [scored[0][1]]

    footer = _format_selection_footer(selected)
    return SourceSelectionResult(selected_sources=tuple(selected), footer=footer)


def select_sources_for_question(question: str, workspace: WorkspaceRuntime, *, fallback_to_all_when_no_match: bool = True) -> SourceSelectionResult:
    readable = _readable_existing_sources(workspace)
    if not readable:
        return SourceSelectionResult(selected_sources=tuple(), footer=None)

    declared = _select_declared_sources(question, readable)
    if declared:
        return SourceSelectionResult(
            selected_sources=tuple(declared),
            footer=_format_selection_footer(declared),
        )

    intent: Intent | None = None
    try:
        manifest = workspace.active_manifest()
        intent = manifest.intent
    except WorkspaceError:
        intent = None

    question_norm = _normalize_for_match(question)
    question_tokens = _tokenize_for_match(question)
    if _question_prefers_multi_source_review(question_norm, question_tokens):
        workspace_relevant = _select_workspace_relevant_sources(question, readable, intent)
        if workspace_relevant:
            return workspace_relevant

    librarian = _select_strong_librarian_sources(question, readable)
    if librarian:
        return librarian

    workspace_relevant = _select_workspace_relevant_sources(question, readable, intent)
    if workspace_relevant:
        return workspace_relevant

    if fallback_to_all_when_no_match:
        return SourceSelectionResult(selected_sources=tuple(readable), footer=_format_selection_footer(readable))
    return SourceSelectionResult(selected_sources=tuple(), footer=None)


def _build_context_from_sources(
    workspace: WorkspaceRuntime,
    readable: list[SourceInfo],
    max_context_bytes: int,
) -> ContextBuildResult:
    if not isinstance(max_context_bytes, int) or max_context_bytes <= 0:
        return ContextBuildResult(ok=False, context_text="", sources_used=tuple(), truncated=False, error="invalid max_context_bytes")

    parts: list[str] = []
    used: list[str] = []
    remaining = max_context_bytes
    truncated = False

    for src in readable:
        header = f"=== source: {src.rel_path} (id: {src.source_id}) ===\n"
        header_b = header.encode("utf-8")
        if len(header_b) > remaining:
            truncated = True
            break
        remaining -= len(header_b)

        try:
            text = workspace.read_source(src.source_id)
        except WorkspaceError:
            continue

        data_b = text.encode("utf-8")
        if len(data_b) > remaining:
            partial = data_b[:remaining].decode("utf-8", errors="replace")
            parts.append(header)
            parts.append(partial)
            used.append(src.rel_path)
            truncated = True
            remaining = 0
            break

        parts.append(header)
        parts.append(text)
        used.append(src.rel_path)
        remaining -= len(data_b)

    context = "\n\n".join(parts).strip() + "\n"
    return ContextBuildResult(ok=True, context_text=context, sources_used=tuple(used), truncated=truncated)


def build_context(
    workspace: WorkspaceRuntime,
    max_context_bytes: int,
    sources: list[SourceInfo] | tuple[SourceInfo, ...] | None = None,
) -> ContextBuildResult:
    if workspace.active_workspace_id is None:
        return ContextBuildResult(
            ok=False,
            context_text="",
            sources_used=tuple(),
            truncated=False,
            error="no active workspace; use: workspace open <id>",
        )

    if sources is None:
        try:
            readable = _readable_existing_sources(workspace)
        except WorkspaceError as exc:
            return ContextBuildResult(ok=False, context_text="", sources_used=tuple(), truncated=False, error=str(exc))
    else:
        readable = list(sources)

    if not readable:
        return ContextBuildResult(
            ok=False,
            context_text="",
            sources_used=tuple(),
            truncated=False,
            error="no declared readable sources available (.md/.txt/.pdf)",
        )

    return _build_context_from_sources(workspace, readable, max_context_bytes)

def _render_model_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    text = re.sub(r"(?is)^\s*answer:\s*", "", text).strip()
    if "\nSources:" in text:
        text = text.split("\nSources:", 1)[0].rstrip()
    return _cleanup_model_answer(text).strip()


def _general_system_prompt() -> str:
    return (
        "You are CCE, a warm and helpful conversational assistant.\n"
        "Answer like a thoughtful teammate: direct, concrete, and lightly conversational.\n"
        "Keep replies short unless the user clearly wants detail.\n"
        "If the user asks about CCE, answer at a high level without inventing internal metrics, affiliations, or specific progress claims.\n"
        "If the user asks about travel or everyday life, answer normally and practically.\n"
        "If you are unsure, say so briefly and naturally.\n"
        "Do not browse. Do not mention sources unless the user explicitly asks for document-grounded behavior.\n"
        "Do not invent a Sources section.\n"
    )


def _general_user_prompt(question: str) -> str:
    return (
        "Respond naturally and helpfully to this conversational question. Keep the tone warm, useful, and non-generic. "
        "Do not echo the question unless that makes the answer clearer. "
        "Do not mention workspace sources unless they are actually being used.\n\n"
        f"Question:\n{question}\n\n"
        "Return format:\n"
        "<concise helpful answer>\n"
    )


def _grounded_system_prompt() -> str:
    return (
        "You are a bounded reasoning component for CCE.\n"
        "Answer ONLY using the provided sources. If the answer is not present, say you cannot find it.\n"
        "Do not use external knowledge. Do not browse. Be concise.\n"
        "For answers with multiple items or times, prefer a short bullet list with one item per line.\n"
        "When the question asks for all items, all flights, all legs, or all departure times, provide an itemized list and include identifying details like flight number, origin, destination, date, and time when they are present in the source.\n"
        "Return only the answer text. Do not include a Sources section; provenance will be appended by the gateway.\n"
    )


def _grounded_user_prompt(question: str, ctx_context: str, itemized_hint: str) -> str:
    return (
        f"Question:\n{question}\n\n"
        f"Sources:\n{ctx_context}\n"
        f"{itemized_hint}"
        "Return format:\n"
        "<short answer or bullet list>\n"
    )


def answer_question(
    *,
    question: str,
    workspace: WorkspaceRuntime,
    model: LocalModel,
    cfg: AskConfig,
    force_grounded: bool = True,
    conversational_fallback_enabled: bool = True,
) -> str:
    question = (question or "").strip()
    if not question:
        return "Usage: ask <question>"

    allow_general = (not force_grounded) and conversational_fallback_enabled

    if workspace.active_workspace_id is None:
        if allow_general:
            resp = model.generate(ModelRequest(system_prompt=_general_system_prompt(), user_prompt=_general_user_prompt(question), timeout_s=cfg.timeout_s))
            if not resp.ok:
                return f"Ask error: model failed: {resp.error}"
            return _render_model_text(resp.text or "")
        return "Ask error: no active workspace; use: workspace open <id>"

    try:
        readable = _readable_existing_sources(workspace)
    except WorkspaceError as exc:
        if allow_general:
            resp = model.generate(ModelRequest(system_prompt=_general_system_prompt(), user_prompt=_general_user_prompt(question), timeout_s=cfg.timeout_s))
            if not resp.ok:
                return f"Ask error: model failed: {resp.error}"
            return _render_model_text(resp.text or "")
        return f"Ask error: {exc}"

    if not readable:
        if allow_general:
            resp = model.generate(ModelRequest(system_prompt=_general_system_prompt(), user_prompt=_general_user_prompt(question), timeout_s=cfg.timeout_s))
            if not resp.ok:
                return f"Ask error: model failed: {resp.error}"
            return _render_model_text(resp.text or "")
        return "Ask error: no declared readable sources available (.md/.txt/.pdf)"

    selection = select_sources_for_question(
        question,
        workspace,
        fallback_to_all_when_no_match=force_grounded or not conversational_fallback_enabled,
    )
    if selection.clarification:
        return selection.clarification

    if allow_general and not selection.selected_sources:
        resp = model.generate(ModelRequest(system_prompt=_general_system_prompt(), user_prompt=_general_user_prompt(question), timeout_s=cfg.timeout_s))
        if not resp.ok:
            return f"Ask error: model failed: {resp.error}"
        return _render_model_text(resp.text or "")

    selected_sources = list(selection.selected_sources) if selection.selected_sources else readable
    ctx = _build_context_from_sources(workspace, selected_sources, cfg.max_context_bytes)
    if not ctx.ok:
        return f"Ask error: {ctx.error}"

    question_norm = _normalize_for_match(question)
    question_tokens = _tokenize_for_match(question)
    itemized_answer = _question_prefers_itemized_answer(question_norm, question_tokens)

    itemized_hint = ""
    if itemized_answer:
        itemized_hint = (
            "The question asks for all matching departures or flights. "
            "Return a bullet list with one bullet per flight or leg, and include flight number, origin, destination, date, and time when those details are present in the source.\n"
        )

    resp = model.generate(
        ModelRequest(
            system_prompt=_grounded_system_prompt(),
            user_prompt=_grounded_user_prompt(question, ctx.context_text, itemized_hint),
            timeout_s=cfg.timeout_s,
        )
    )
    if not resp.ok:
        return f"Ask error: model failed: {resp.error}"

    rendered = _render_model_text(resp.text or "")
    if selection.footer:
        rendered = f"{rendered}\n\n{selection.footer}".rstrip()

    if ctx.truncated:
        return rendered.strip() + "\n\n[truncation: context limited]\n"
    return rendered.strip()

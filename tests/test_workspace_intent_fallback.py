import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from gateway.ask import AskConfig, answer_question, select_sources_for_question
from models.interface import LocalModel, ModelRequest, ModelResponse
from workspace_runtime.manifest import Intent, load_manifest
from workspace_runtime.runtime import WorkspaceRuntime


class _TrackingModel(LocalModel):
    def __init__(self, text: str = "Answer:\nOK\n\nSources:\n- none") -> None:
        self._text = text
        self.last_request: ModelRequest | None = None

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        return ModelResponse(ok=True, text=self._text)


def _source(**kwargs):
    defaults = dict(
        exists=True,
        supported_type=True,
        display_name=None,
        kind=None,
        category=None,
        keywords=(),
        aliases=(),
    )
    defaults.update(kwargs)
    return mock.Mock(**defaults)


def _intent() -> Intent:
    return Intent(
        domains=("travel", "itinerary", "logistics"),
        keywords=("flight", "layover", "connection", "itinerary", "trip", "fragile", "contingency"),
        entities=("dallas", "dfw", "chattanooga", "missoula", "montana"),
    )


class WorkspaceIntentFallbackTests(unittest.TestCase):
    def test_manifest_parses_workspace_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws_dir = Path(tmp) / "intent-workspace"
            ws_dir.mkdir()
            (ws_dir / "workspace.toml").write_text(
                "\n".join(
                    [
                        'workspace_id = "intent-workspace"',
                        'title = "Intent Workspace"',
                        '',
                        '[intent]',
                        'domains = ["travel"]',
                        'keywords = ["flight", "layover"]',
                        'entities = ["dallas", "dfw"]',
                    ]
                ),
                encoding="utf-8",
            )
            manifest = load_manifest(ws_dir / "workspace.toml")

        assert manifest.intent is not None
        self.assertEqual(manifest.intent.domains, ("travel",))
        self.assertEqual(manifest.intent.keywords, ("flight", "layover"))
        self.assertEqual(manifest.intent.entities, ("dallas", "dfw"))

    def test_dallas_layover_stays_in_grounded_lane(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "montana-trip"
        fake_ws.active_manifest.return_value = SimpleNamespace(intent=_intent())
        fake_ws.sources.return_value = [
            _source(
                source_id="aa_trip_confirmation",
                rel_path="sources/AA trip confirmation CHA—MSO.pdf",
                display_name="AA Trip Confirmation",
                kind="pdf",
                category="flight",
                keywords=("flight", "dfw", "departure", "arrival", "return"),
                aliases=("aa confirmation",),
            ),
            _source(
                source_id="itinerary_summary",
                rel_path="sources/itinerary-summary.md",
                display_name="Itinerary Summary",
                kind="document",
                category="itinerary",
                keywords=("itinerary", "schedule", "trip"),
                aliases=("itinerary summary",),
            ),
            _source(source_id="notes", rel_path="notes.md", display_name="Workspace Notes", kind="notes", category="notes"),
        ]
        fake_ws.read_source.side_effect = {
            "aa_trip_confirmation": "AA PDF",
            "itinerary_summary": "ITINERARY",
            "notes": "NOTES",
        }.__getitem__

        model = _TrackingModel("Answer:\n3 hours 17 minutes\n\nSources:\n- none")
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)
        out = answer_question(
            question="How much layover time do I have in Dallas?",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
            force_grounded=False,
        )

        self.assertIn("3 hours 17 minutes", out)
        self.assertIn("AA Trip Confirmation", out)
        assert model.last_request is not None
        self.assertIn("bounded reasoning component", model.last_request.system_prompt)
        self.assertNotIn("warm and helpful conversational assistant", model.last_request.system_prompt)

    def test_out_of_domain_question_still_uses_general_conversation(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "montana-trip"
        fake_ws.active_manifest.return_value = SimpleNamespace(intent=_intent())
        fake_ws.sources.return_value = [
            _source(source_id="aa_trip_confirmation", rel_path="sources/aa.pdf", display_name="AA Trip Confirmation", kind="pdf", category="flight"),
        ]

        model = _TrackingModel("Answer:\nParis\n\nSources:\n- none")
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)
        out = answer_question(
            question="What is the capital of France?",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
            force_grounded=False,
        )

        self.assertIn("Paris", out)
        self.assertNotIn("AA Trip Confirmation", out)
        assert model.last_request is not None
        self.assertIn("warm and helpful conversational assistant", model.last_request.system_prompt)

    def test_ambiguous_workspace_question_asks_human_readable_clarification(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "montana-trip"
        fake_ws.active_manifest.return_value = SimpleNamespace(intent=Intent(domains=("travel",), keywords=("connection",), entities=("dallas",)))
        fake_ws.sources.return_value = [
            _source(source_id="aa_trip_confirmation", rel_path="sources/aa.pdf", display_name="AA Trip Confirmation", kind="pdf", category="flight"),
            _source(source_id="itinerary_summary", rel_path="sources/itinerary-summary.md", display_name="Itinerary Summary", kind="document", category="flight"),
        ]

        selection = select_sources_for_question("How long is my connection?", fake_ws, fallback_to_all_when_no_match=False)
        self.assertEqual(selection.selected_sources, tuple())
        self.assertIsNotNone(selection.clarification)
        self.assertIn("AA Trip Confirmation", selection.clarification or "")
        self.assertIn("Itinerary Summary", selection.clarification or "")
        self.assertNotIn("Reply with `use <source_id>`", selection.clarification or "")

    def test_multi_source_workspace_question_selects_small_set(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "montana-trip"
        fake_ws.active_manifest.return_value = SimpleNamespace(intent=_intent())
        fake_ws.sources.return_value = [
            _source(source_id="contingency_planning", rel_path="sources/contingency.md", display_name="Contingency Planning", kind="plan", category="contingency", keywords=("contingency", "backup", "delay")),
            _source(source_id="aa_trip_confirmation", rel_path="sources/aa.pdf", display_name="AA Trip Confirmation", kind="pdf", category="flight", keywords=("flight", "return", "departure")),
            _source(source_id="itinerary_summary", rel_path="sources/itinerary-summary.md", display_name="Itinerary Summary", kind="document", category="itinerary", keywords=("itinerary", "trip", "plan")),
            _source(source_id="travel_insurance_plan", rel_path="sources/insurance.pdf", display_name="Travel Insurance Plan", kind="pdf", category="insurance", keywords=("insurance", "coverage")),
            _source(source_id="notes", rel_path="notes.md", display_name="Workspace Notes", kind="notes", category="notes"),
        ]

        selection = select_sources_for_question("What parts of my Montana trip plan look fragile?", fake_ws, fallback_to_all_when_no_match=False)
        selected_ids = [src.source_id for src in selection.selected_sources]
        self.assertIn("contingency_planning", selected_ids)
        self.assertLessEqual(len(selected_ids), 3)
        self.assertIsNone(selection.clarification)

    def test_explicit_source_selection_still_wins_with_intent_enabled(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "montana-trip"
        fake_ws.active_manifest.return_value = SimpleNamespace(intent=_intent())
        fake_ws.sources.return_value = [
            _source(source_id="aa_trip_confirmation", rel_path="sources/aa.pdf", display_name="AA Trip Confirmation", kind="pdf", category="flight"),
            _source(source_id="itinerary_summary", rel_path="sources/itinerary-summary.md", display_name="Itinerary Summary", kind="document", category="itinerary"),
        ]

        selection = select_sources_for_question("Using aa_trip_confirmation only, what is the time?", fake_ws)
        self.assertEqual([src.source_id for src in selection.selected_sources], ["aa_trip_confirmation"])
        self.assertEqual(selection.footer, "- AA Trip Confirmation")

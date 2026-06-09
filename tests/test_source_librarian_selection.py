import unittest
from unittest import mock

from gateway.ask import AskConfig, answer_question, select_sources_for_question, _format_selection_footer
from models.interface import LocalModel, ModelRequest, ModelResponse
from workspace_runtime.runtime import WorkspaceRuntime


class _StaticModel(LocalModel):
    def __init__(self, text: str) -> None:
        self._text = text

    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(ok=True, text=self._text)


def _source(**kwargs):
    defaults = dict(
        exists=True,
        supported_type=True,
        display_name=None,
        category=None,
        keywords=(),
        aliases=(),
    )
    defaults.update(kwargs)
    return mock.Mock(**defaults)


class SourceLibrarianSelectionTests(unittest.TestCase):
    def test_single_best_match_selects_one_source_and_footer(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="aa_trip_confirmation",
                rel_path="sources/AA trip confirmation CHA—MSO.pdf",
                display_name="AA Trip Confirmation",
                category="flight",
                keywords=("flight", "dfw", "cha", "departure"),
                aliases=("aa confirmation", "return flight"),
            ),
            _source(
                source_id="sportsmans_lodge_confirmation_a",
                rel_path="sources/Sportsmans Lodge confirmation confirmation number LL45125QLB.pdf",
                display_name="Sportsman's Lodge Confirmation",
                category="lodging",
                keywords=("lodge", "stay"),
                aliases=("sportsmans lodge",),
            ),
        ]

        selection = select_sources_for_question("When does my return flight from DFW to Chattanooga leave?", fake_ws)
        self.assertEqual([src.source_id for src in selection.selected_sources], ["aa_trip_confirmation"])
        self.assertEqual(selection.footer, "- AA Trip Confirmation")
        self.assertIsNone(selection.clarification)

    def test_multi_source_question_selects_small_set(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="aa_trip_confirmation",
                rel_path="sources/AA trip confirmation CHA—MSO.pdf",
                display_name="AA Trip Confirmation",
                category="flight",
                keywords=("flight", "dfw", "cha", "departure", "leave", "return"),
                aliases=("aa confirmation", "return flight"),
            ),
            _source(
                source_id="sportsmans_lodge_confirmation_a",
                rel_path="sources/Sportsmans Lodge confirmation confirmation number LL45125QLB.pdf",
                display_name="Sportsman's Lodge Confirmation",
                category="lodging",
                keywords=("lodge", "leave", "before", "flight", "departure"),
                aliases=("sportsmans lodge", "lodge confirmation"),
            ),
            _source(
                source_id="travel_insurance_plan",
                rel_path="sources/Travel insurance plan EUSP2558794819.pdf",
                display_name="Travel Insurance Plan",
                category="insurance",
                keywords=("insurance", "policy"),
                aliases=("travel insurance",),
            ),
        ]

        selection = select_sources_for_question(
            "What time should I leave the lodge to make my return flight?",
            fake_ws,
        )
        selected_ids = [src.source_id for src in selection.selected_sources]
        self.assertEqual(selected_ids[:2], ["aa_trip_confirmation", "sportsmans_lodge_confirmation_a"])
        self.assertLessEqual(len(selected_ids), 3)
        self.assertEqual(
            selection.footer,
            "- AA Trip Confirmation\n- Sportsman's Lodge Confirmation",
        )
        self.assertIsNone(selection.clarification)

    def test_duplicate_display_names_are_deduped_in_footer(self) -> None:
        sources = [
            _source(
                source_id="sportsmans_lodge_confirmation_a",
                rel_path="sources/Sportsmans Lodge confirmation confirmation number LL45125QLB.pdf",
                display_name="Sportsman's Lodge Confirmation",
            ),
            _source(
                source_id="sportsmans_lodge_confirmation_b",
                rel_path="sources/Sportsmans Lodge confirmationconfirmation number LL45125QLD.pdf",
                display_name="Sportsman's Lodge Confirmation",
            ),
        ]

        self.assertEqual(_format_selection_footer(sources), "- Sportsman's Lodge Confirmation")

    def test_single_fact_tie_requests_clarification(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="alpha",
                rel_path="sources/a.md",
                display_name="Alpha",
                category="travel",
                keywords=("depart",),
            ),
            _source(
                source_id="beta",
                rel_path="sources/b.md",
                display_name="Beta",
                category="travel",
                keywords=("depart",),
            ),
        ]

        selection = select_sources_for_question("When does it depart?", fake_ws)
        self.assertEqual(selection.selected_sources, tuple())
        self.assertIsNone(selection.footer)
        self.assertIsNotNone(selection.clarification)
        self.assertIn("Alpha", selection.clarification or "")
        self.assertIn("Beta", selection.clarification or "")

    def test_no_metadata_falls_back_to_all_readable_sources(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(source_id="a", rel_path="sources/a.md", display_name="Source A"),
            _source(source_id="b", rel_path="sources/b.md", display_name="Source B"),
        ]

        selection = select_sources_for_question("Tell me something", fake_ws)
        self.assertEqual([src.source_id for src in selection.selected_sources], ["a", "b"])
        self.assertEqual(selection.footer, "- Source A\n- Source B")
        self.assertIsNone(selection.clarification)

    def test_answer_question_includes_selection_footer(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="aa_trip_confirmation",
                rel_path="sources/AA trip confirmation CHA—MSO.pdf",
                display_name="AA Trip Confirmation",
                category="flight",
                keywords=("flight", "dfw", "cha", "departure", "leave"),
                aliases=("aa confirmation", "return flight"),
            ),
            _source(
                source_id="sportsmans_lodge_confirmation_a",
                rel_path="sources/Sportsmans Lodge confirmation confirmation number LL45125QLB.pdf",
                display_name="Sportsman's Lodge Confirmation",
                category="lodging",
                keywords=("lodge", "stay"),
                aliases=("sportsmans lodge",),
            ),
        ]
        fake_ws.read_source.side_effect = {
            "aa_trip_confirmation": "AA PDF",
            "sportsmans_lodge_confirmation_a": "LODGE PDF",
        }.__getitem__

        model = _StaticModel("Answer:\n12:38 PM\n\nSources:\n- None")
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)
        out = answer_question(
            question="When does my return flight from DFW to Chattanooga leave?",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
        )
        self.assertNotIn("Answer:", out)
        self.assertIn("12:38 PM", out)
        self.assertIn("- AA Trip Confirmation", out)
        self.assertNotIn("Sources:", out)
        self.assertNotIn("sportsmans", out.lower())

    def test_answer_question_cleans_duplicate_words_and_wrapped_times(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="aa_trip_confirmation",
                rel_path="sources/AA trip confirmation CHA—MSO.pdf",
                display_name="AA Trip Confirmation",
                category="flight",
                keywords=("flight", "dfw", "cha", "departure", "leave"),
                aliases=("aa confirmation", "return flight"),
            ),
        ]
        fake_ws.read_source.return_value = "AA PDF"

        model = _StaticModel(
            "Answer:\n"
            "The departure times for your outbound legs from Tennessee to Montana are 6:\n"
            "6:00 AM on June 19, 2026 from Chattanooga and 6:45 AM on June 23, 2026 from\n"
            "from Missoula."
        )
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)
        out = answer_question(
            question="Please provide all the departure times for all my outbound legs from Tennessee to Montana.",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
        )
        self.assertIn("6:00 AM on June 19, 2026 from Chattanooga", out)
        self.assertIn("6:45 AM on June 23, 2026 from Missoula", out)
        self.assertNotIn("from from", out)
        self.assertNotIn("6:\n6:00", out)
        self.assertIn("- AA Trip Confirmation", out)

    def test_answer_question_cleans_wrapped_bullets_and_split_words(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="aa_trip_confirmation",
                rel_path="sources/AA trip confirmation CHA—MSO.pdf",
                display_name="AA Trip Confirmation",
                category="flight",
                keywords=("flight", "dfw", "cha", "departure", "leave"),
                aliases=("aa confirmation", "return flight"),
            ),
            _source(
                source_id="sportsmans_lodge_confirmation_a",
                rel_path="sources/lodge.pdf",
                display_name="Sportsman's Lodge Confirmation",
                category="lodging",
                keywords=("lodge", "stay"),
                aliases=("sportsmans lodge",),
            ),
        ]
        fake_ws.read_source.side_effect = {
            "aa_trip_confirmation": "AA PDF",
            "sportsmans_lodge_confirmation_a": "LODGE PDF",
        }.__getitem__

        model = _StaticModel(
            "Answer:\n"
            "• Two identical Sportsmans Lodge reservations (Confirmations LL45125QLB and\n"
            "and LL45125QLD) booked for the exact same dates and Quee\n"
            "Queen Cabin.\n"
            "• Tight return connection on Tuesday, June 23: AA 3924 arrives in DFW at 11\n"
            "11:09 AM and AA 3522 departs for CHA at 12:38 PM, leaving only a 1-hour 29-\n"
            "29-minute layover.\n"
            "The capital of France is Paris. Let me know if you need histor\n"
            "historical context."
        )
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)
        out = answer_question(
            question="What parts of my trip look fragile?",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
        )
        self.assertIn("LL45125QLB and LL45125QLD", out)
        self.assertIn("Queen Cabin", out)
        self.assertIn("11:09 AM", out)
        self.assertIn("1-hour 29-minute layover", out)
        self.assertIn("historical context", out)
        self.assertNotIn("and and", out)
        self.assertNotIn("Quee Queen", out)
        self.assertNotIn("11 11:09", out)
        self.assertNotIn("29- 29-minute", out)
        self.assertNotIn("histor historical", out)

    def test_answer_question_strips_angle_wrappers_and_quantity_wraps(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="aa_trip_confirmation",
                rel_path="sources/AA trip confirmation CHA—MSO.pdf",
                display_name="AA Trip Confirmation",
                category="flight",
                keywords=("flight", "dfw", "cha", "departure", "leave"),
                aliases=("aa confirmation", "return flight"),
            ),
        ]
        fake_ws.read_source.side_effect = {
            "aa_trip_confirmation": "AA PDF",
        }.__getitem__

        model = _StaticModel(
            "Answer:\n"
            "• Tight return connection: the DFW layover is only 1 hour 2\n"
            "29 minutes between flights.\n"
            "• Duplicate hotel booking: confirmations LL45125QLB and L\n"
            "LL45125QLD exist for the same dates in the Quee\n"
            "Queen Cabin.\n"
            "<Paris. Let me know if you need histor\n"
            "historical context.>"
        )
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)
        out = answer_question(
            question="What parts of my trip look fragile?",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
        )
        self.assertIn("1 hour 29 minutes", out)
        self.assertIn("LL45125QLB and LL45125QLD", out)
        self.assertIn("Queen Cabin", out)
        self.assertIn("Paris. Let me know if you need historical context.", out)
        self.assertNotIn("1 hour 2 29 minutes", out)
        self.assertNotIn("L LL45125QLD", out)
        self.assertNotIn("Quee Queen", out)
        self.assertNotIn("<Paris.", out)
        self.assertNotIn("context.>", out)
        self.assertNotIn("histor historical", out)

    def test_answer_question_strips_single_letter_wrapped_prefixes(self) -> None:
        fake_ws = mock.Mock(spec=WorkspaceRuntime)
        fake_ws.active_workspace_id = "ws"
        fake_ws.sources.return_value = [
            _source(
                source_id="travel_notes",
                rel_path="notes.md",
                display_name="Travel Notes",
                category="trip",
                keywords=("travel",),
                aliases=("notes",),
            ),
        ]
        fake_ws.read_source.side_effect = {
            "travel_notes": "notes",
        }.__getitem__

        model = _StaticModel(
            "Answer:\n"
            "Paris. Let me know if you're planning a visit or j\n"
            "just curious."
        )
        cfg = AskConfig(provider="ollama", model_name="m", max_context_bytes=5000, timeout_s=1)
        out = answer_question(
            question="What is the capital of France?",
            workspace=fake_ws,
            model=model,
            cfg=cfg,
        )
        self.assertIn("visit or just curious.", out)
        self.assertNotIn("or j just curious", out)

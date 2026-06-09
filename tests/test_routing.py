import unittest

from gateway.routing import decide_route


class RoutingTests(unittest.TestCase):
    def test_blank_is_ignored(self) -> None:
        self.assertEqual(decide_route("   ", has_active_workspace=False).action, "ignore")

    def test_explicit_ask_routes_to_ask(self) -> None:
        d = decide_route("ask what", has_active_workspace=False)
        self.assertEqual(d.action, "ask")
        self.assertEqual(d.question, "what")
        self.assertTrue(d.force_grounded)

    def test_known_commands_route_to_command(self) -> None:
        for msg in ["status", "workspace list", "workspace open x", "workspace status", "sources", "read readme"]:
            self.assertEqual(decide_route(msg, has_active_workspace=True).action, "command")

    def test_command_like_unknown_does_not_route_to_model(self) -> None:
        for msg in ["delete everything", "shell ls", "exec whoami", "pem show", "model pick"]:
            self.assertEqual(decide_route(msg, has_active_workspace=True).action, "help")

    def test_ordinary_text_routes_to_ask_regardless_of_workspace_state(self) -> None:
        self.assertEqual(decide_route("what is in this workspace?", has_active_workspace=True).action, "ask")
        self.assertEqual(decide_route("what is in this workspace?", has_active_workspace=False).action, "ask")
        self.assertFalse(decide_route("what is in this workspace?", has_active_workspace=False).force_grounded)


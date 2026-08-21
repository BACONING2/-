import threading
import unittest
from unittest.mock import patch

import numpy as np

import main


class WaitForStepResultTests(unittest.TestCase):
    @patch("main.capture_screen")
    def test_waits_for_screen_change_before_returning(self, capture_mock):
        base = np.zeros((4, 4, 3), dtype=np.uint8)
        changed = np.full((4, 4, 3), 255, dtype=np.uint8)
        capture_mock.side_effect = [base, changed]

        start = main.wait_for_step_result({"after_wait": 0.5}, "demo", None, timeout=0.5)

        self.assertTrue(start)

    @patch("main.capture_screen")
    @patch("main.match_all_templates")
    def test_waits_for_new_template_result(self, match_mock, capture_mock):
        base = np.zeros((4, 4, 3), dtype=np.uint8)
        capture_mock.side_effect = [base, base, base]
        match_mock.side_effect = [
            {"old": ((1, 1), 0.9)},
            {"new": ((2, 2), 0.95)},
        ]

        result = main.wait_for_step_result({"after_wait": 0.5, "wait_for": "time"}, "old", None, timeout=0.5)

        self.assertTrue(result)

    def test_match_all_templates_respects_click_point_radius(self):
        screen = np.zeros((200, 200, 3), dtype=np.uint8)
        template = np.zeros((20, 20, 3), dtype=np.uint8)
        template[5:15, 5:15] = 255
        templates = {"near_target": template}

        match = main.match_all_templates(screen, templates, threshold=0.8, search_center=(100, 100), search_radius=30)
        self.assertIsNone(match["near_target"][0])

        screen[90:110, 90:110] = template
        match = main.match_all_templates(screen, templates, threshold=0.8, search_center=(100, 100), search_radius=30)
        self.assertIsNotNone(match["near_target"][0])

    def test_match_all_templates_respects_selected_rect_region(self):
        screen = np.zeros((200, 200, 3), dtype=np.uint8)
        template = np.zeros((20, 20, 3), dtype=np.uint8)
        template[5:15, 5:15] = 255
        templates = {"selected_region": template}

        match = main.match_all_templates(screen, templates, threshold=0.8, search_rect=(90, 90, 110, 110))
        self.assertIsNone(match["selected_region"][0])

        screen[90:110, 90:110] = template
        match = main.match_all_templates(screen, templates, threshold=0.8, search_rect=(90, 90, 110, 110))
        self.assertIsNotNone(match["selected_region"][0])

    def test_match_task_templates_expands_selected_rect_after_miss(self):
        screen = np.zeros((200, 200, 3), dtype=np.uint8)
        template = np.zeros((20, 20, 3), dtype=np.uint8)
        template[5:15, 5:15] = 255
        screen[70:90, 70:90] = template
        main.templates = {"expanded": template}

        match = main.match_task_templates(
            {"match_rect": (90, 90, 110, 110)},
            screen,
            ["expanded"],
        )

        self.assertIsNotNone(match["expanded"][0])

    def test_match_task_templates_stops_at_screen_bounds(self):
        screen = np.zeros((40, 60, 3), dtype=np.uint8)
        template = np.zeros((5, 5, 3), dtype=np.uint8)
        template[1:4, 1:4] = 255
        main.templates = {"missing": template}

        with patch("main.match_all_templates", wraps=main.match_all_templates) as match_mock:
            match = main.match_task_templates(
                {"match_rect": (20, 15, 25, 20)},
                screen,
                ["missing"],
            )

        self.assertIsNone(match["missing"][0])
        self.assertEqual(match_mock.call_args.kwargs["search_rect"], (0, 0, 60, 40))

    @patch("main.click_global_position")
    @patch("main.match_task_templates", return_value={})
    @patch("main.capture_screen")
    def test_click_until_gone_checks_change_immediately_after_click(self, capture_mock, match_mock, click_mock):
        unchanged = np.zeros((4, 4, 3), dtype=np.uint8)
        changed = np.full((4, 4, 3), 255, dtype=np.uint8)
        capture_mock.side_effect = [unchanged, unchanged, changed]

        result = main.execute_click_until_gone_task(
            {
                "template": "",
                "click_position": (10, 20),
                "stop_on_change": True,
                "click_interval": 0.5,
                "timeout": 1,
            }
        )

        self.assertTrue(result)
        click_mock.assert_called_once()
        match_mock.assert_not_called()

    @patch("main.match_all_templates")
    @patch("main.capture_screen")
    def test_wait_for_step_result_uses_next_template_region(self, capture_mock, match_mock):
        screen = np.zeros((20, 20, 3), dtype=np.uint8)
        capture_mock.side_effect = [screen, screen]
        match_mock.return_value = {"next": ((5, 5), 0.95)}

        result = main.wait_for_step_result(
            {
                "wait_for": "next_appear",
                "next_match_rect": (1, 2, 10, 12),
            },
            next_template_names=["next"],
        )

        self.assertTrue(result)
        self.assertEqual(match_mock.call_args.kwargs["search_rect"], (1, 2, 10, 12))

    @patch("main.wait_for_step_result")
    @patch("main.pyautogui.keyUp")
    @patch("main.pyautogui.keyDown")
    @patch("main.time.sleep")
    def test_keyboard_move_uses_before_and_after_delays(self, sleep_mock, key_down_mock, key_up_mock, wait_mock):
        result = main.execute_keyboard_move_task(
            {
                "move_steps": [{"key": "W", "duration": 0.2}],
                "delay_before": 0.4,
                "after_wait": 0.6,
            }
        )

        self.assertTrue(result)
        self.assertEqual(sleep_mock.call_args_list[0].args[0], 0.4)
        self.assertEqual(sleep_mock.call_args_list[-1].args[0], 0.6)

    @patch("main.click_global_position")
    @patch("main.wait_for_step_result")
    @patch("main.match_task_templates", return_value={"demo": ((10, 10), 0.9)})
    @patch("main.capture_screen")
    @patch("main.time.sleep")
    def test_normal_step_waits_after_completion(self, sleep_mock, capture_mock, match_mock, wait_mock, click_mock):
        capture_mock.return_value = np.zeros((20, 20, 3), dtype=np.uint8)

        result = main.execute_task(
            {"template": "demo", "after_wait": 0.7, "click": True, "timeout": 1}
        )

        self.assertTrue(result)
        self.assertEqual(sleep_mock.call_args_list[-1].args[0], 0.7)

    @patch("main.execute_task")
    def test_run_task_queue_accepts_one_based_jump_number(self, execute_task_mock):
        tasks = [{"template": f"task_{i}"} for i in range(1, 11)]
        visited = []

        def fake_execute(task, stop_flag=None, log_callback=None):
            visited.append(task["template"])
            if task["template"] == "task_1":
                return {"outer_jump_to": 10}
            return True

        execute_task_mock.side_effect = fake_execute

        main.run_task_queue(tasks, log_callback=lambda *args, **kwargs: None)

        self.assertIn("task_10", visited)
        self.assertEqual(visited[0], "task_1")
        self.assertEqual(visited[-1], "task_10")
        self.assertEqual(visited.count("task_10"), 1)

    @patch("main.execute_task")
    def test_run_task_queue_resolves_jump_against_original_flow_numbers(self, execute_task_mock):
        tasks = [
            {"template": "task_1", "_outer_step_number": 1},
            {"template": "task_10", "_outer_step_number": 10},
        ]
        visited = []

        def fake_execute(task, stop_flag=None, log_callback=None):
            visited.append(task["template"])
            if task["template"] == "task_1":
                return {"outer_jump_to": 10}
            return True

        execute_task_mock.side_effect = fake_execute

        main.run_task_queue(tasks, log_callback=lambda *args, **kwargs: None)

        self.assertEqual(visited, ["task_1", "task_10"])

    @patch("main.execute_task")
    def test_run_task_queue_ignores_self_outer_jump_to_avoid_infinite_loop(self, execute_task_mock):
        tasks = [{"template": "task_1"}]
        call_count = {"value": 0}

        def fake_execute(task, stop_flag=None, log_callback=None):
            call_count["value"] += 1
            if call_count["value"] == 1:
                return {"outer_jump_to": 1}
            return True

        execute_task_mock.side_effect = fake_execute

        main.run_task_queue(tasks, log_callback=lambda *args, **kwargs: None)

        self.assertEqual(call_count["value"], 1)

    @patch("main.execute_task")
    def test_detour_child_cannot_trigger_outer_jump(self, execute_task_mock):
        detour = {"template": "detour_step", "detour_enabled": True, "detour_steps": [{"template": "nested"}]}
        log_callback = lambda *args, **kwargs: None

        execute_task_mock.return_value = True
        self.assertTrue(main.execute_detour_task(detour, log_callback=log_callback))

        execute_task_mock.assert_called_once_with(
            {"template": "nested"},
            stop_flag=None,
            log_callback=log_callback,
            allow_detour=False,
        )

    @patch("main.execute_detour_task", return_value=True)
    @patch("main.match_task_templates", return_value={"detour_step": (None, -1.0)})
    @patch("main.capture_screen")
    def test_enabled_empty_detour_can_jump_to_number(self, capture_mock, match_mock, detour_mock):
        capture_mock.return_value = np.zeros((20, 20, 3), dtype=np.uint8)

        result = main.execute_task(
            {
                "template": "detour_step",
                "timeout": 1,
                "click": False,
                "detour_enabled": True,
                "detour_steps": [],
                "detour_jump_to": 8,
            }
        )

        self.assertEqual(result, {"outer_jump_to": 8})
        detour_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

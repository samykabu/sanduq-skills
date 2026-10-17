"""Browser-free harness tests; pixel/timer regressions live in --self-test."""
import unittest
from unittest.mock import ANY, Mock, call, patch

from _helpers import load

lint = load("lint-render.py")


class CaptureClockTests(unittest.TestCase):
    def test_screenshot_restores_precapture_styles_without_restoring_outer_mutations(self):
        page = Mock()
        snapshots = page.evaluate_handle.return_value
        page.screenshot.return_value = b"png"
        sequence = Mock()
        sequence.attach_mock(page.evaluate_handle, "snapshot")
        sequence.attach_mock(page.screenshot, "screenshot")
        sequence.attach_mock(snapshots, "styles")
        self.assertEqual(lint.shoot(page), b"png")
        self.assertEqual(sequence.mock_calls, [
            call.snapshot(lint.CAPTURE_STYLES_JS), call.screenshot(animations="disabled"),
            call.styles.evaluate(lint.RESTORE_CAPTURE_STYLES_JS), call.styles.dispose()])
        page.evaluate.assert_not_called()  # no outer RESTORE_JS or shared stack

    def test_screenshot_exception_still_restores_styles_and_disposes_snapshot(self):
        page = Mock()
        page.screenshot.side_effect = RuntimeError("capture failed")
        snapshots = page.evaluate_handle.return_value
        with self.assertRaisesRegex(RuntimeError, "capture failed"):
            lint.shoot(page)
        self.assertEqual(snapshots.mock_calls, [
            call.evaluate(lint.RESTORE_CAPTURE_STYLES_JS), call.dispose()])

    def test_snapshot_is_disposed_even_if_restoring_styles_fails(self):
        page = Mock()
        snapshots = page.evaluate_handle.return_value
        snapshots.evaluate.side_effect = RuntimeError("restore failed")
        with self.assertRaisesRegex(RuntimeError, "restore failed"):
            lint.shoot(page)
        snapshots.dispose.assert_called_once_with()

    def test_install_and_pause_once_per_context(self):
        context = Mock()
        lint.prepare_context(context)
        lint.prepare_context(context)
        self.assertEqual(context.clock.mock_calls, [call.install(time=0), call.pause_at(1)])

    def test_failed_install_is_not_marked_ready(self):
        context = Mock()
        context.clock.install.side_effect = RuntimeError("install failed")
        with self.assertRaisesRegex(RuntimeError, "install failed"):
            lint.prepare_context(context)
        self.assertNotIn(context, lint._CLOCK_CONTEXTS)

    def test_each_new_page_is_paused_even_when_context_is_already_installed(self):
        context = Mock()
        lint.prepare_context(context)
        pages = [Mock(context=context), Mock(context=context)]
        for page in pages:
            # Preserve fractional milliseconds exactly, including the epoch
            # after another fixture explicitly advanced time by one ms.
            page.evaluate.return_value = "1970-01-01T00:00:01.001Z"
            sequence = Mock()
            sequence.attach_mock(page.evaluate, "evaluate")
            sequence.attach_mock(page.clock, "clock")
            lint.prepare_page(page)
            self.assertEqual(sequence.mock_calls, [
                call.evaluate("() => new Date().toISOString()"),
                call.clock.pause_at("1970-01-01T00:00:01.001Z")])
        context.clock.install.assert_called_once_with(time=0)
        context.clock.pause_at.assert_called_once_with(1)

    def test_same_page_can_be_bootstrapped_again_after_navigation(self):
        page = Mock()
        page.evaluate.side_effect = ["1970-01-01T00:00:01.001Z", "1970-01-01T00:00:01.002Z"]
        lint.prepare_page(page)
        lint.prepare_page(page)
        self.assertEqual(page.clock.pause_at.call_args_list, [
            call("1970-01-01T00:00:01.001Z"), call("1970-01-01T00:00:01.002Z")])

    def test_fixture_clock_bootstrap_precedes_set_content(self):
        context = Mock()
        page = Mock(context=context)
        context.new_page.return_value = page
        page.evaluate.return_value = "1970-01-01T00:00:01.001Z"
        page.set_content.side_effect = RuntimeError("stop before fixture scripts")
        sequence = Mock()
        sequence.attach_mock(page.clock, "clock")
        sequence.attach_mock(page.set_content, "set_content")
        with self.assertRaisesRegex(RuntimeError, "stop before fixture scripts"):
            lint.timer_comparison_failures(context)
        self.assertEqual(sequence.mock_calls, [
            call.clock.pause_at("1970-01-01T00:00:01.001Z"),
            call.set_content(ANY)])

    def test_unprepared_measurement_fails_before_touching_document(self):
        page = Mock()
        with self.assertRaisesRegex(RuntimeError, "before loading"):
            lint.measure(page)
        page.evaluate.assert_not_called()

    def test_all_reveal_steps_are_sampled_in_time_order(self):
        page = Mock()
        page.evaluate.return_value = [{"count": 3, "hold": 900}, {"count": 2, "hold": 720}]
        self.assertEqual(lint.reveal_frame_times(page), [0, 720, 900, 1440, 1800, 2700])

    def test_static_pages_retain_initial_measurement(self):
        page = Mock()
        page.evaluate.return_value = []
        self.assertEqual(lint.reveal_frame_times(page), [0])

    def test_invalid_declarations_fail_instead_of_silently_losing_coverage(self):
        for count, hold in ((0, 720), (9, 720), (1.5, 720), (None, 720),
                            (float("nan"), 720), (3, 300), (8, 1200)):
            with self.subTest(count=count, hold=hold):
                page = Mock()
                page.evaluate.return_value = [{"count": count, "hold": hold}]
                with self.assertRaises(ValueError):
                    lint.reveal_frame_times(page)

    def test_navigation_follows_clock_setup_and_each_frame_is_measured(self):
        page = Mock()
        page.evaluate.return_value = "1970-01-01T00:00:01.001Z"
        path = Mock()
        path.resolve.return_value.as_uri.return_value = "file:///figure.html"
        sequence = Mock()
        sequence.attach_mock(page.context.clock, "clock")
        sequence.attach_mock(page.goto, "goto")
        sequence.attach_mock(page.clock, "page_clock")
        with patch.object(lint, "watch"), patch.object(lint, "reveal_frame_times", return_value=[0, 720, 1440]), \
                patch.object(lint, "measure", side_effect=[[], [("clipped", "actual spill")], [("clipped", "actual spill")]]) as measure:
            sequence.attach_mock(measure, "measure")
            self.assertEqual(lint.check(page, path), [("clipped", "actual spill")])
        self.assertEqual(sequence.mock_calls, [
            call.clock.install(time=0), call.clock.pause_at(1),
            call.goto("file:///figure.html", wait_until="load"),
            call.page_clock.pause_at("1970-01-01T00:00:01.001Z"), call.measure(page),
            call.clock.run_for(720), call.measure(page),
            call.clock.run_for(720), call.measure(page)])

    def test_pair_restores_styles_when_a_screenshot_fails(self):
        page = Mock()
        lint.prepare_context(page.context)
        with patch.object(lint, "shoot", side_effect=RuntimeError("capture failed")):
            with self.assertRaisesRegex(RuntimeError, "capture failed"):
                lint.compare_release(page, 0, 1, 0.25)
        self.assertEqual(page.evaluate.mock_calls, [
            call(lint.SET_SCALE_JS, [0, 0.25]), call(lint.RESTORE_JS)])

    def test_pair_rejects_uncontrolled_time_before_mutation(self):
        page = Mock()
        with self.assertRaisesRegex(RuntimeError, "before loading"):
            lint.compare_release(page, 0, 0, 1)
        page.evaluate.assert_not_called()


if __name__ == "__main__":
    unittest.main()

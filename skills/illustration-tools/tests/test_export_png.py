"""PNG export: exact viewBox x scale pixels, transparency, bounded waits, the complete static motion frame."""
import contextlib
import importlib.util
import io
import struct
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from _helpers import run_cli

SKILL = Path(__file__).resolve().parents[1] / "skills" / "illustrate"
spec = importlib.util.spec_from_file_location("export_diagram", SKILL / "scripts" / "export_diagram.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

FIGURE = ('<svg viewBox="0 0 {w} {h}" style="width:100%"><rect x="2" y="2" width="20" height="10" fill="#c026d3"/>'
          '<rect x="{edge}" y="2" width="10" height="10" fill="#c026d3"/></svg>')


def png_size(path):
    with open(path, "rb") as handle:
        header = handle.read(24)
    return struct.unpack(">II", header[16:24])


def page(folder, name, figure, head="", body_attrs=""):
    path = Path(folder) / name
    path.write_text(f"<!doctype html><html><head>{head}</head><body {body_attrs}>"
                    f'<div style="width:300px;overflow:hidden">{figure}</div></body></html>', encoding="utf-8")
    return path


class _Stall(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        time.sleep(20)
        with contextlib.suppress(OSError):  # the exporter cancelled the request long ago
            self.send_error(500)

    def log_message(self, *args):
        pass


class PngExportTests(unittest.TestCase):
    def setUp(self):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("Playwright and Pillow are needed for PNG export checks")

    def test_fractional_scale_gives_exact_viewbox_pixels_with_transparency(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            # The figure is wider than its 300px clipping frame; the PNG is still the whole viewBox.
            source = page(tmp, "wide.html", FIGURE.format(w=640, h=96, edge=620))
            for scale, expected in ((1, (640, 96)), (1.25, (800, 120)), (2.5, (1600, 240)), (4, (2560, 384))):
                with self.subTest(scale=scale):
                    out = Path(tmp) / f"wide-{scale}.png"
                    self.assertEqual(export.write_png(source, out, scale), expected)
                    self.assertEqual(png_size(out), expected)
                    image = Image.open(out).convert("RGBA")
                    self.assertEqual(image.getpixel((image.width - 1, image.height - 1))[3], 0, "background is transparent")
                    probe = image.getpixel((int(625 * scale), int(7 * scale)))
                    self.assertGreater(probe[3], 200, "the right-edge node was clipped")

    def test_subpixel_position_preserves_exact_dimensions_and_content(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            for width, height, scale in ((101, 101, 1.25), (1024, 640, 1.5)):
                with self.subTest(scale=scale):
                    source = page(tmp, "offset.html", FIGURE.format(w=width, h=height, edge=width - 15),
                                  "<style>svg{display:block}</style>", 'style="margin:0.5px"')
                    out = Path(tmp) / "offset.png"
                    expected = round(width * scale), round(height * scale)
                    self.assertEqual(export.write_png(source, out, scale, system_fonts=True), expected)
                    self.assertEqual(png_size(out), expected)
                    with Image.open(out) as png:
                        image = png.convert("RGBA")
                        self.assertEqual(image.getpixel((image.width - 1, image.height - 1))[3], 0)
                        self.assertGreater(image.getpixel((int((width - 10) * scale), int(7 * scale)))[3], 200)

    def test_motion_figure_is_captured_on_its_complete_static_frame(self):
        from PIL import Image
        motion = SKILL / "assets" / "template-motion.html"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "motion.png"
            figure = motion.read_text(encoding="utf-8")
            box = export.safe.ensure_viewbox(figure[slice(*export.figure_span(figure))])
            self.assertEqual(export.write_png(motion, out, 1), (round(box[2]), round(box[3])))
            self.assertGreater(sum(Image.open(out).convert("RGBA").getchannel("A").histogram()[1:]), 1000)
            stuck = page(tmp, "stuck.html", FIGURE.format(w=100, h=40, edge=80))
            stuck.write_text(stuck.read_text(encoding="utf-8").replace(
                "<div ", '<div data-motion-root data-frame="start" '), encoding="utf-8")
            with self.assertRaisesRegex(export.ExportError, "complete static frame"):
                export.write_png(stuck, Path(tmp) / "stuck.png", 1)

    def test_a_stalled_font_request_is_cancelled_with_a_warning(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Stall)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                head = f'<link rel="stylesheet" href="http://127.0.0.1:{server.server_port}/stall.css">'
                source = page(tmp, "stall.html", FIGURE.format(w=120, h=40, edge=100), head)
                out = Path(tmp) / "stall.png"
                stderr = io.StringIO()
                started = time.monotonic()
                with contextlib.redirect_stderr(stderr):
                    export.write_png(source, out, 1, network_idle_timeout_ms=1500, fallback_settle_ms=100)
                self.assertLess(time.monotonic() - started, 15)
                self.assertIn("fallback typography", stderr.getvalue())
                self.assertEqual(png_size(out), (120, 40))
                # Offline mode aborts remote requests instead of waiting for them.
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    export.write_png(source, out, 1, system_fonts=True, network_idle_timeout_ms=5000)
                self.assertNotIn("fallback typography", stderr.getvalue())
        finally:
            server.shutdown()

    def test_cli_keeps_names_for_odd_filenames_and_keeps_the_svg_when_png_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = page(tmp, "a #1 50%.html", FIGURE.format(w=120, h=40, edge=100))
            code, out = run_cli("export_diagram.py", source, "--scale", "1.5", "--system-fonts")
            self.assertEqual(code, 0, out)
            self.assertEqual(png_size(Path(tmp) / "a #1 50%.png"), (180, 60))
            self.assertTrue((Path(tmp) / "a #1 50%.svg").is_file())
            broken = page(tmp, "broken.html", FIGURE.format(w=120, h=40, edge=100))
            broken.write_text(broken.read_text(encoding="utf-8").replace(
                "<div ", '<div data-motion-root data-frame="step" '), encoding="utf-8")
            code, out = run_cli("export_diagram.py", broken, "--system-fonts")
            self.assertEqual(code, 2)
            self.assertIn(str((Path(tmp) / "broken.svg").resolve()), out)
            self.assertIn("export error:", out)
            self.assertTrue((Path(tmp) / "broken.svg").is_file())
            self.assertFalse((Path(tmp) / "broken.png").exists())


if __name__ == "__main__":
    unittest.main()

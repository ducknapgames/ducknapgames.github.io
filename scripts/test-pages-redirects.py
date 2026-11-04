"""Check the Pages-only artifact against real published routes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("pages_redirects", Path(__file__).with_name("build-pages-redirects.py"))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class PagesRedirects(unittest.TestCase):
    def test_published_routes_redirect_and_preserve_home_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "pages"
            before = (builder.ROOT / "index.html").read_bytes()
            routes = builder.build(builder.ROOT, output)
            self.assertGreaterEqual(len(routes), 160)
            for path, target in routes.items():
                with self.subTest(route=path):
                    text = (output / path).read_text(encoding="utf-8")
                    self.assertIn('content="0;url=' + target + '"', text)
                    self.assertIn('rel="canonical" href="' + target + '"', text)
                    self.assertIn("location.search + location.hash", text)
                    self.assertNotIn('class="studio-home"', text)
            self.assertIn("google-site-verification", (output / "index.html").read_text(encoding="utf-8"))
            self.assertEqual((output / "app-ads.txt").read_bytes(), (builder.ROOT / "app-ads.txt").read_bytes())
            self.assertEqual((builder.ROOT / "index.html").read_bytes(), before)
            self.assertIn("Allow: /", (output / "robots.txt").read_text(encoding="utf-8"))

    def test_refuses_to_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            sentinel = output / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                builder.build(builder.ROOT, output)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()

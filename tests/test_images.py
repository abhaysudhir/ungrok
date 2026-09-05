"""Offline tests for optional request-image resizing. No original files are changed."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resize_image.py"
SPEC = importlib.util.spec_from_file_location("ungrok_resize_image", SCRIPT)
resize = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resize)


@unittest.skipIf(Image is None, "Optional Pillow dependency is not installed")
class ResizeImageTests(unittest.TestCase):
    def image_payload(self, size=(20, 10), mode="RGB", color="red", fmt="PNG", **save_options):
        with Image.new(mode, size, color) as source:
            out = io.BytesIO()
            source.save(out, format=fmt, **save_options)
        return {"data": base64.b64encode(out.getvalue()).decode("ascii")}

    def decoded(self, result):
        self.assertEqual(result["mimeType"], "image/jpeg")
        image = Image.open(io.BytesIO(base64.b64decode(result["data"], validate=True)))
        image.load()
        self.addCleanup(image.close)
        return image

    def test_resize_preserves_aspect_ratio_and_original_payload(self):
        payload = self.image_payload(size=(3200, 1600))
        original = dict(payload)
        result = self.decoded(resize.resize_payload(payload))
        self.assertEqual(result.size, (1568, 784))
        self.assertEqual(result.mode, "RGB")
        self.assertEqual(payload, original)

    def test_small_image_is_not_upscaled(self):
        self.assertEqual(self.decoded(resize.resize_payload(self.image_payload())).size, (20, 10))

    def test_alpha_is_composited_on_white(self):
        result = self.decoded(resize.resize_payload(self.image_payload(mode="RGBA", color=(255, 0, 0, 0))))
        self.assertTrue(all(value >= 250 for value in result.getpixel((0, 0))))

    def test_exif_orientation_is_applied_and_metadata_removed(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "SYNTHETIC_TEST_METADATA"
        payload = self.image_payload(size=(100, 50), fmt="JPEG", exif=exif)
        result = self.decoded(resize.resize_payload(payload))
        self.assertEqual(result.size, (50, 100))
        self.assertEqual(dict(result.getexif()), {})
        self.assertNotIn(b"SYNTHETIC_TEST_METADATA", base64.b64decode(resize.resize_payload(payload)["data"]))

    def test_animation_uses_first_frame(self):
        with Image.new("RGB", (10, 10), "red") as first, Image.new("RGB", (10, 10), "blue") as second:
            out = io.BytesIO()
            first.save(out, format="GIF", save_all=True, append_images=[second], loop=0)
        result = self.decoded(resize.resize_payload({"data": base64.b64encode(out.getvalue()).decode()}))
        red, green, blue = result.getpixel((0, 0))
        self.assertGreater(red, 240)
        self.assertLess(blue, 20)

    def test_bad_data_and_unsupported_format_fail_without_echoing_content(self):
        for payload in ({}, None, {"data": 1}, {"data": "PRIVATE not-base64"},
                        {"data": base64.b64encode(b"PRIVATE not-an-image").decode()},
                        self.image_payload(fmt="BMP")):
            with self.subTest(payload_type=type(payload).__name__):
                with self.assertRaises(resize.ImageFailure) as error:
                    resize.resize_payload(payload)
                self.assertNotIn("PRIVATE", str(error.exception))

    def test_decode_pixel_limit_rejects_before_image_load(self):
        payload = self.image_payload(size=(11, 10))
        # Lower the production limit instead of allocating a decompression bomb.
        with mock.patch.object(resize, "MAX_PIXELS", 100):
            with self.assertRaisesRegex(resize.ImageFailure, "decode limit"):
                resize.resize_payload(payload)

    def test_decompression_bomb_error_is_content_free(self):
        payload = self.image_payload(size=(20, 20))
        with mock.patch.object(resize, "MAX_PIXELS", 100):
            with self.assertRaisesRegex(resize.ImageFailure, "decode limit"):
                resize.resize_payload(payload)

    def test_input_and_output_size_limits(self):
        payload = self.image_payload()
        with mock.patch.object(resize, "MAX_INPUT_BYTES", 10):
            with self.assertRaisesRegex(resize.ImageFailure, "input limit"):
                resize.resize_payload(payload)
        with mock.patch.object(resize, "MAX_OUTPUT_BYTES", 10):
            with self.assertRaisesRegex(resize.ImageFailure, "output limit"):
                resize.resize_payload(payload)

    def test_stdin_stdout_protocol(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(self.image_payload()).encode(),
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        self.assertEqual(self.decoded(json.loads(result.stdout)).size, (20, 10))

    def test_protocol_failure_has_no_stdout_or_traceback(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=b"PRIVATE invalid json",
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"PRIVATE", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()

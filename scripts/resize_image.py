#!/usr/bin/env python3
"""Resize a request-only image copy in memory. Optional dependency: Pillow.

Protocol: stdin JSON {"data": "<strict base64>"}; stdout JSON
{"mimeType": "image/jpeg", "data": "<base64>"}. No paths are accepted or
written. Originals remain untouched. Animated images use the first frame.
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import sys
import warnings

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_JSON_BYTES = ((MAX_INPUT_BYTES + 2) // 3) * 4 + 1024
MAX_PIXELS = 40_000_000
MAX_EDGE = 1568
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
MAX_ADDRESS_SPACE = 1024 * 1024 * 1024


class ImageFailure(Exception):
    """Fixed, content-free error safe to show in logs."""


def resize_payload(payload):
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        raise ImageFailure("Pillow is not installed for the configured Python runtime.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), str):
        raise ImageFailure("Expected JSON containing a base64 data string.")
    encoded = payload["data"]
    if len(encoded) > ((MAX_INPUT_BYTES + 2) // 3) * 4:
        raise ImageFailure("Image exceeds the 20 MiB input limit.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ImageFailure("Image data is not valid base64.") from None
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise ImageFailure("Image is empty or exceeds the 20 MiB input limit.")
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ALLOWED_FORMATS:
                    raise ImageFailure("Only JPEG, PNG, WebP, and GIF images are supported.")
                width, height = source.size
                if width < 1 or height < 1 or width * height > MAX_PIXELS:
                    raise ImageFailure("Image exceeds the 40 megapixel decode limit.")
                # JPEG can decode directly at reduced resolution before allocation.
                source.draft("RGB", (MAX_EDGE, MAX_EDGE))
                source.seek(0)
                oriented = ImageOps.exif_transpose(source)
                try:
                    oriented.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
                    # A fresh RGB canvas removes EXIF, comments, and other metadata.
                    rgb = Image.new("RGB", oriented.size, "white")
                    try:
                        if "A" in oriented.getbands() or "transparency" in oriented.info:
                            with oriented.convert("RGBA") as rgba:
                                with rgba.getchannel("A") as alpha:
                                    rgb.paste(rgba, mask=alpha)
                        else:
                            rgb.paste(oriented)
                        output = io.BytesIO()
                        rgb.save(output, format="JPEG", quality=85, optimize=True)
                        result = output.getvalue()
                    finally:
                        rgb.close()
                finally:
                    oriented.close()
        if len(result) > MAX_OUTPUT_BYTES:
            raise ImageFailure("Resized image exceeds the 4 MiB output limit.")
        return {"mimeType": "image/jpeg", "data": base64.b64encode(result).decode("ascii")}
    except ImageFailure:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageFailure("Image exceeds the 40 megapixel decode limit.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, MemoryError):
        raise ImageFailure("Image could not be decoded or resized safely.") from None


def main():
    try:
        # The supported host is Linux. Bound decoder allocations as well as input
        # bytes/pixels; retain any stricter limits supplied by the caller.
        if sys.platform == "linux":
            import resource
            for kind, maximum in ((resource.RLIMIT_AS, MAX_ADDRESS_SPACE), (resource.RLIMIT_CPU, 20)):
                soft, hard = resource.getrlimit(kind)
                bound = min(maximum, hard) if hard != resource.RLIM_INFINITY else maximum
                bound = min(bound, soft) if soft != resource.RLIM_INFINITY else bound
                resource.setrlimit(kind, (bound, hard))
        raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise ImageFailure("Image request exceeds the input limit.")
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError, RecursionError):
            raise ImageFailure("Image request is not valid JSON.") from None
        result = resize_payload(payload)
        sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
        return 0
    except ImageFailure as error:
        print(f"ungrok image resize: {error}", file=sys.stderr)
        return 2
    except (OSError, MemoryError):
        print("ungrok image resize: resource limit or I/O failure.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

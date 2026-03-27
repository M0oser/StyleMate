import os
import subprocess
import tempfile
from io import BytesIO
from typing import Tuple

from PIL import Image, ImageOps


HEIC_EXTENSIONS = {"heic", "heif"}
HEIC_CONTENT_TYPES = {"image/heic", "image/heif"}


def _file_ext(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower().strip()


def _is_heic(filename: str, content_type: str) -> bool:
    return _file_ext(filename) in HEIC_EXTENSIONS or (content_type or "").lower().strip() in HEIC_CONTENT_TYPES


def _decode_with_sips(image_bytes: bytes, filename: str) -> Image.Image:
    ext = _file_ext(filename) or "heic"
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = os.path.join(tmpdir, f"input.{ext}")
        target_path = os.path.join(tmpdir, "converted.jpg")

        with open(source_path, "wb") as f:
            f.write(image_bytes)

        subprocess.run(
            ["/usr/bin/sips", "-s", "format", "jpeg", source_path, "--out", target_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with Image.open(target_path) as img:
            return ImageOps.exif_transpose(img).convert("RGB")


def load_normalized_image(image_bytes: bytes, filename: str, content_type: str) -> Image.Image:
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            return ImageOps.exif_transpose(img).convert("RGB")
    except Exception:
        if _is_heic(filename, content_type):
            return _decode_with_sips(image_bytes, filename)
        raise


def normalize_upload_image(
    image_bytes: bytes,
    filename: str,
    content_type: str,
) -> Tuple[bytes, str, str]:
    image = load_normalized_image(image_bytes, filename, content_type)

    base_name = os.path.splitext(filename or "upload")[0] or "upload"
    normalized_filename = f"{base_name}.jpg"

    output = BytesIO()
    image.save(output, format="JPEG", quality=95)
    return output.getvalue(), normalized_filename, "image/jpeg"

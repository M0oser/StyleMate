import os
from typing import Dict, Tuple

import httpx

from backend.services.vision_local import (
    LocalVisionUnavailable,
    analyze_image_local,
    save_analysis_json,
)


def _remote_headers() -> Dict[str, str]:
    return {
        "X-Pinggy-No-Screen": "1",
        "Bypass-Tunnel-Reminder": "true",
        "User-Agent": "StyleMateBackend/1.0",
    }


async def analyze_image_remote(
    image_bytes: bytes,
    filename: str,
    content_type: str,
    vision_api_url: str,
) -> Dict:
    files = {
        "file": (
            filename,
            image_bytes,
            content_type or "image/jpeg",
        )
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            vision_api_url,
            files=files,
            headers=_remote_headers(),
            follow_redirects=True,
        )

    if response.status_code != 200:
        raise httpx.HTTPStatusError(
            f"Vision service returned {response.status_code}",
            request=response.request,
            response=response,
        )

    data = response.json()
    data["source"] = "remote"
    return data


async def analyze_uploaded_clothing(
    image_path: str,
    image_bytes: bytes,
    filename: str,
    content_type: str,
    json_output_path: str,
) -> Tuple[Dict, str]:
    mode = os.getenv("VISION_MODE", "auto").lower().strip()
    vision_api_url = os.getenv("VISION_API_URL", "https://stylemate2026.loca.lt/")

    last_error = None

    if mode in {"local", "auto"}:
        try:
            analysis = analyze_image_local(image_path).to_dict()
            save_analysis_json(analysis, json_output_path)
            return analysis, "local"
        except Exception as e:
            last_error = e
            if mode == "local":
                raise

    if mode in {"remote", "auto"}:
        analysis = await analyze_image_remote(
            image_bytes=image_bytes,
            filename=filename,
            content_type=content_type,
            vision_api_url=vision_api_url,
        )
        save_analysis_json(analysis, json_output_path)
        return analysis, "remote"

    raise LocalVisionUnavailable(f"Unsupported VISION_MODE={mode}; last_error={last_error}")

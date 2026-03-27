from __future__ import annotations

import json
import logging
import os
from typing import Any

from parsers.utils import format_price


LOGGER = logging.getLogger(__name__)

DEFAULT_HTTP_TIMEOUT = 20
DEFAULT_OLLAMA_TIMEOUT = 180
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct"


def build_outfit_prompt(
    occasion: str,
    style: str,
    candidate_outfits: list[dict[str, Any]],
    wardrobe_items: list[dict[str, Any]] | None = None,
) -> str:
    """Build a strict JSON-only prompt for the stylist model."""
    outfit_count = len(candidate_outfits)
    valid_indexes = list(range(1, outfit_count + 1))
    outfit_lines: list[str] = []
    for index, outfit in enumerate(candidate_outfits, start=1):
        outfit_lines.append(f"Outfit {index}:")
        for item in outfit.get("items", []):
            outfit_lines.append(
                "- {title} | category={category} | color={color} | price={price}".format(
                    title=item.get("title") or "Untitled",
                    category=item.get("category") or "unknown",
                    color=item.get("color") or "unknown",
                    price=format_price(item.get("price"), item.get("currency")),
                )
            )
        outfit_lines.append("")

    outfits_block = "\n".join(outfit_lines).strip()
    example_scores = ",\n".join(
        [
            "    {\n"
            f'      "index": {index},\n'
            '      "score": 8,\n'
            '      "reason": "..."\n'
            "    }"
            for index in valid_indexes
        ]
    )

    return (
        "You are a fashion stylist AI.\n"
        "Your task is to rank candidate outfits for a user request.\n\n"
        "You MUST follow these rules exactly:\n"
        "1. You must evaluate EVERY outfit candidate.\n"
        f'2. There are exactly {outfit_count} outfit candidates.\n'
        f'3. Candidate indexes are exactly: {valid_indexes}.\n'
        f'4. You MUST return exactly {outfit_count} score objects.\n'
        '5. Each score object MUST include "index", "score", and "reason".\n'
        '6. "best_index" MUST be one of the provided candidate indexes.\n'
        "7. Return ONLY valid JSON.\n"
        "8. Do NOT include markdown.\n"
        "9. Do NOT include explanation outside JSON.\n"
        "10. Do NOT invent clothes that are not in the candidates.\n"
        "11. Your job is only to rank the provided outfits.\n\n"
        "Scoring criteria:\n"
        "- occasion fit\n"
        "- style fit\n"
        "- color harmony\n"
        "- silhouette balance\n"
        "- overall coherence\n\n"
        "User request:\n"
        f'occasion = "{occasion}"\n'
        f'style = "{style}"\n\n'
        "Candidate outfits:\n"
        f"{outfits_block}\n\n"
        "You must return JSON in EXACTLY this format:\n"
        "{\n"
        f'  "best_index": {valid_indexes[0] if valid_indexes else 1},\n'
        '  "scores": [\n'
        f"{example_scores}\n"
        "  ],\n"
        '  "final_reason": "..."\n'
        "}\n\n"
        "Validation rule:\n"
        '- every candidate index appears exactly once in "scores"\n'
        "- no candidate index is missing\n"
        "- no extra candidate index exists\n"
        "- score must be an integer from 1 to 10\n"
        "- reasons must be concise\n\n"
        "Return ONLY JSON.\n"
    )


def call_local_model(prompt: str) -> str:
    """
    Call a local model adapter.

    Supported modes:
    - STYLIST_MODEL_BACKEND=stub
    - STYLIST_MODEL_BACKEND=http with STYLIST_MODEL_ENDPOINT
    - STYLIST_MODEL_BACKEND=ollama
    - auto mode: endpoint -> ollama -> stub
    """
    backend = (
        os.getenv("STYLIST_MODEL_BACKEND")
        or os.getenv("STYLIST_MODEL_PROVIDER")
        or "auto"
    ).strip().lower()

    try:
        if backend == "http":
            return _call_http_model(prompt)
        if backend == "ollama":
            return _call_ollama_model(prompt)
        if backend == "stub":
            return _build_stub_response(prompt)

        if os.getenv("STYLIST_OLLAMA_MODEL") or os.getenv("STYLIST_MODEL_NAME") or os.getenv("OLLAMA_MODEL"):
            return _call_ollama_model(prompt)
        if os.getenv("STYLIST_MODEL_ENDPOINT"):
            return _call_http_model(prompt)
    except Exception:
        LOGGER.exception("AI stylist model call failed")
        raise

    return _build_stub_response(prompt)


def parse_model_response(response_text: str, outfit_count: int) -> dict[str, Any]:
    """Parse and validate model JSON response."""
    if not response_text:
        raise ValueError("Model returned empty response")

    payload = _extract_json_object(response_text)
    best_index = int(payload["best_index"])
    if best_index < 1 or best_index > outfit_count:
        raise ValueError(f"best_index out of range: {best_index}")

    raw_scores = payload.get("scores")
    if not isinstance(raw_scores, list) or not raw_scores:
        raise ValueError("scores must be a non-empty list")

    normalized_scores: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()

    for entry in raw_scores:
        if not isinstance(entry, dict):
            continue

        index = int(entry["index"])
        if index < 1 or index > outfit_count or index in seen_indexes:
            continue

        score = int(entry["score"])
        score = max(1, min(10, score))
        reason = str(entry.get("reason") or "").strip()

        normalized_scores.append(
            {
                "index": index,
                "score": score,
                "reason": reason,
            }
        )
        seen_indexes.add(index)

    if not normalized_scores:
        raise ValueError("Model response does not contain usable scores")
    if len(normalized_scores) != outfit_count:
        raise ValueError(
            f"Model response must score every outfit candidate (expected {outfit_count}, got {len(normalized_scores)})"
        )
    if best_index not in seen_indexes:
        raise ValueError("best_index must also appear in scores")

    return {
        "best_index": best_index,
        "scores": normalized_scores,
        "final_reason": str(payload.get("final_reason") or "").strip(),
    }


def rank_outfits_with_model(
    occasion: str,
    style: str,
    candidate_outfits: list[dict[str, Any]],
    wardrobe_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rank already-generated candidate outfits with an optional model layer."""
    if not candidate_outfits:
        return {
            "outfits": [],
            "used_ai": False,
            "fallback_used": True,
            "error": "No candidate outfits provided",
            "final_reason": "",
        }

    prompt = build_outfit_prompt(
        occasion=occasion,
        style=style,
        candidate_outfits=candidate_outfits,
        wardrobe_items=wardrobe_items,
    )

    try:
        raw_response = call_local_model(prompt)
        parsed = parse_model_response(raw_response, len(candidate_outfits))
        ranked_outfits = _apply_model_ranking(candidate_outfits, parsed)
        return {
            "outfits": ranked_outfits,
            "used_ai": True,
            "fallback_used": False,
            "error": None,
            "final_reason": parsed.get("final_reason") or "",
            "raw_response": raw_response,
        }
    except Exception as error:
        LOGGER.exception("Falling back to rule-based outfit order")
        return {
            "outfits": _apply_rule_fallback(candidate_outfits, str(error)),
            "used_ai": False,
            "fallback_used": True,
            "error": str(error),
            "final_reason": "AI stylist unavailable. Showing rule-based ranking.",
            "raw_response": None,
        }


def _call_http_model(prompt: str) -> str:
    import requests

    endpoint = os.getenv("STYLIST_MODEL_ENDPOINT")
    if not endpoint:
        raise RuntimeError("STYLIST_MODEL_ENDPOINT is not configured")

    timeout = int(os.getenv("STYLIST_MODEL_TIMEOUT", DEFAULT_HTTP_TIMEOUT))
    response = requests.post(
        endpoint,
        json={"prompt": prompt},
        timeout=timeout,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError:
        return response.text

    for key in ("response", "output", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return json.dumps(payload, ensure_ascii=False)


def _call_ollama_model(prompt: str) -> str:
    import requests

    host = (
        os.getenv("STYLIST_OLLAMA_HOST")
        or os.getenv("STYLIST_MODEL_ENDPOINT")
        or DEFAULT_OLLAMA_HOST
    ).rstrip("/")
    model = (
        os.getenv("STYLIST_OLLAMA_MODEL")
        or os.getenv("STYLIST_MODEL_NAME")
        or os.getenv("OLLAMA_MODEL")
        or DEFAULT_OLLAMA_MODEL
    )
    timeout = int(
        os.getenv(
            "STYLIST_OLLAMA_TIMEOUT",
            os.getenv("STYLIST_MODEL_TIMEOUT", DEFAULT_OLLAMA_TIMEOUT),
        )
    )

    response = requests.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": 256,
            },
        },
        timeout=(10, timeout),
    )
    response.raise_for_status()
    payload = response.json()
    model_response = payload.get("response")
    if not isinstance(model_response, str) or not model_response.strip():
        raise ValueError("Ollama returned empty response")
    return model_response


def _build_stub_response(prompt: str) -> str:
    outfit_count = prompt.count("Outfit ")
    if outfit_count <= 0:
        outfit_count = 1

    scores = []
    for index in range(1, outfit_count + 1):
        score = max(1, 9 - (index - 1))
        scores.append(
            {
                "index": index,
                "score": score,
                "reason": "Fallback ranking used because no live model is configured.",
            }
        )

    return json.dumps(
        {
            "best_index": 1,
            "scores": scores,
            "final_reason": "Fallback AI response selected the first generated outfit.",
        },
        ensure_ascii=False,
    )


def _extract_json_object(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")

    payload = json.loads(cleaned[start:end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Model response JSON must be an object")
    return payload


def _apply_model_ranking(
    candidate_outfits: list[dict[str, Any]],
    parsed: dict[str, Any],
) -> list[dict[str, Any]]:
    score_map = {entry["index"]: entry for entry in parsed["scores"]}
    best_index = parsed["best_index"]
    final_reason = parsed.get("final_reason") or ""

    decorated: list[tuple[tuple[int, int, int], dict[str, Any]]] = []
    for original_position, outfit in enumerate(candidate_outfits, start=1):
        score_entry = score_map.get(original_position, {})
        ai_score = score_entry.get("score")
        ai_reason = score_entry.get("reason") or ""
        enriched = dict(outfit)
        enriched["ai_score"] = ai_score
        enriched["ai_reason"] = ai_reason
        enriched["ai_best"] = original_position == best_index
        enriched["ai_final_reason"] = final_reason
        enriched["ranking_source"] = "ai"
        enriched["model_index"] = original_position
        decorated.append(
            (
                (
                    0 if original_position == best_index else 1,
                    -(ai_score if ai_score is not None else -1),
                    original_position,
                ),
                enriched,
            )
        )

    decorated.sort(key=lambda item: item[0])
    return [item[1] for item in decorated]


def _apply_rule_fallback(
    candidate_outfits: list[dict[str, Any]],
    error_message: str,
) -> list[dict[str, Any]]:
    fallback_reason = "AI stylist unavailable. Showing rule-based ranking."
    if error_message:
        fallback_reason = f"{fallback_reason} ({error_message})"

    ranked: list[dict[str, Any]] = []
    for index, outfit in enumerate(candidate_outfits, start=1):
        enriched = dict(outfit)
        enriched["ai_score"] = None
        enriched["ai_reason"] = ""
        enriched["ai_best"] = index == 1
        enriched["ai_final_reason"] = fallback_reason
        enriched["ranking_source"] = "rule"
        enriched["model_index"] = index
        ranked.append(enriched)
    return ranked

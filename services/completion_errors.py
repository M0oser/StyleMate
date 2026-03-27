from __future__ import annotations

from typing import Any


class CompletionAPIError(Exception):
    """Machine-readable domain error for completion API integration."""

    code = "COMPLETION_ERROR"
    status_code = 400
    default_message = "Completion request failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details or {}


class InvalidRequestError(CompletionAPIError):
    code = "INVALID_REQUEST"
    status_code = 400
    default_message = "Request payload is invalid."


class NoAnchorsSelectedError(CompletionAPIError):
    code = "NO_ANCHORS_SELECTED"
    status_code = 400
    default_message = "At least one anchor wardrobe item must be selected."


class InvalidScenarioError(CompletionAPIError):
    code = "INVALID_SCENARIO"
    status_code = 400
    default_message = "Scenario is not supported."


class InvalidSeasonError(CompletionAPIError):
    code = "INVALID_SEASON"
    status_code = 400
    default_message = "Season is not supported."


class AnchorsNotFoundError(CompletionAPIError):
    code = "ANCHORS_NOT_FOUND"
    status_code = 404
    default_message = "Selected wardrobe items were not found."

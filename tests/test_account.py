"""Tests for the client-capability gate on URL-mode sign-in prompts.

Regression cover: the first version treated "client declared nothing" as
"client cannot do URL prompts", so the prompt was never sent and sign-in
silently degraded to pasting a URL.
"""

from __future__ import annotations

from types import SimpleNamespace

from spotify_mcp.tools.account import _url_elicitation_refused


def _ctx(capabilities: object) -> object:
    return SimpleNamespace(client_capabilities=capabilities)


def test_no_capabilities_is_not_a_refusal():
    """Capabilities can arrive per request, so silence must not block the prompt."""
    assert _url_elicitation_refused(_ctx(None)) is False


def test_no_elicitation_capability_is_not_a_refusal():
    caps = SimpleNamespace(elicitation=None)

    assert _url_elicitation_refused(_ctx(caps)) is False


def test_elicitation_without_url_mode_is_a_refusal():
    caps = SimpleNamespace(elicitation=SimpleNamespace(form={}, url=None))

    assert _url_elicitation_refused(_ctx(caps)) is True


def test_elicitation_with_url_mode_is_not_a_refusal():
    caps = SimpleNamespace(elicitation=SimpleNamespace(form={}, url={}))

    assert _url_elicitation_refused(_ctx(caps)) is False

"""Regression: the fallback must open the browser, not hand back a dead URL.

The loopback listener that catches Spotify's redirect only lives for the
duration of the `authenticate` call. Returning "open this URL yourself" in an
error therefore points at a closed port — sign-in can never complete that way.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from spotify_mcp.tools import account

AUTH_URL = "https://accounts.spotify.com/authorize?client_id=probe"


class _StubClient:
    async def __aenter__(self) -> _StubClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return {"display_name": "Tester", "id": "tester"}


@pytest.fixture()
def wired(monkeypatch: pytest.MonkeyPatch):
    """Run `authenticate` with the OAuth flow reduced to a single present() call."""
    opened: list[str] = []
    monkeypatch.setattr(account, "missing_credentials", lambda: [])
    monkeypatch.setattr(account, "SpotifyClient", _StubClient)

    async def fake_authorize(present, timeout: float = 300.0) -> dict[str, Any]:
        await present(AUTH_URL)
        return {"access_token": "t"}

    monkeypatch.setattr(account, "authorize", fake_authorize)
    monkeypatch.setattr(account, "_open_locally", lambda url: opened.append(url) or True)
    return opened


def _ctx(*, elicit_error: Exception | None = None, action: str | None = None):
    async def elicit_url(**kwargs: Any):
        if elicit_error is not None:
            raise elicit_error
        return SimpleNamespace(action=action)

    async def send_elicit_complete(elicitation_id: str) -> None:
        return None

    return SimpleNamespace(
        client_capabilities=None,
        elicit_url=elicit_url,
        session=SimpleNamespace(send_elicit_complete=send_elicit_complete),
    )


@pytest.mark.asyncio
async def test_browser_opens_when_the_client_prompt_fails(wired):
    ctx = _ctx(elicit_error=RuntimeError("no back-channel"))
    result = json.loads(await account.authenticate(ctx))

    assert wired == [AUTH_URL], "fallback must open the browser while the listener is up"
    assert result["status"] == "signed_in"


@pytest.mark.asyncio
async def test_browser_opens_when_client_refuses_url_mode(monkeypatch, wired):
    monkeypatch.setattr(account, "_url_elicitation_refused", lambda ctx: True)

    result = json.loads(await account.authenticate(_ctx()))

    assert wired == [AUTH_URL]
    assert result["status"] == "signed_in"


@pytest.mark.asyncio
async def test_accepted_prompt_does_not_open_a_second_browser(wired):
    result = json.loads(await account.authenticate(_ctx(action="accept")))

    assert wired == []
    assert result["status"] == "signed_in"


@pytest.mark.asyncio
async def test_declined_prompt_raises_instead_of_falling_back(wired):
    with pytest.raises(RuntimeError, match="declineed|declined"):
        await account.authenticate(_ctx(action="decline"))

    assert wired == [], "a declined prompt is a decision, not a failure to prompt"


@pytest.mark.asyncio
async def test_error_says_the_url_alone_will_not_work(monkeypatch, wired):
    monkeypatch.setattr(account, "_open_locally", lambda url: False)

    with pytest.raises(RuntimeError, match="nothing is listening"):
        await account.authenticate(_ctx(elicit_error=RuntimeError("no back-channel")))

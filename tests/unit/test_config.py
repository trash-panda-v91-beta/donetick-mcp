"""Unit tests for base URL validation."""

import pytest

from donetick_mcp.config import Config


def test_https_required_by_default():
    with pytest.raises(ValueError, match="HTTPS"):
        Config(
            donetick_base_url="http://donetick.selfhosted.svc.cluster.local:2021",
            donetick_api_token="tok",
        )


def test_insecure_http_opt_in():
    c = Config(
        donetick_base_url="http://donetick.selfhosted.svc.cluster.local:2021",
        donetick_api_token="tok",
        allow_insecure_http=True,
    )
    assert c.donetick_base_url == "http://donetick.selfhosted.svc.cluster.local:2021"


def test_insecure_http_from_env(monkeypatch):
    monkeypatch.setenv("ALLOW_INSECURE_HTTP", "true")
    c = Config(
        donetick_base_url="http://donetick.selfhosted.svc.cluster.local:2021",
        donetick_api_token="tok",
    )
    assert c.allow_insecure_http is True

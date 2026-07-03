"""Tests for equser.api modules.

Requires requests (``[analysis]`` extra). HTTP calls are tested via
construction/URL building only (no actual network calls).
"""

import importlib.util

import pytest

HAS_REQUESTS = importlib.util.find_spec("requests") is not None
HAS_WEBSOCKET = importlib.util.find_spec("websocket") is not None  # websocket-client

pytestmark = pytest.mark.skipif(not HAS_REQUESTS, reason="requests not installed")


class TestGatewayClient:
    def test_default_url(self):
        from equser.api.client import GatewayClient
        client = GatewayClient()
        assert client.base_url == 'http://localhost'

    def test_custom_url(self):
        from equser.api.client import GatewayClient
        client = GatewayClient('http://192.168.10.1:8080/')
        assert client.base_url == 'http://192.168.10.1:8080'

    def test_custom_timeout(self):
        from equser.api.client import GatewayClient
        client = GatewayClient(timeout=120)
        assert client.timeout == 120

    def test_url_trailing_slash_stripped(self):
        from equser.api.client import GatewayClient
        client = GatewayClient('http://host:8080///')
        assert not client.base_url.endswith('/')


class TestSynapseClientRemoved:
    """The deprecated SynapseClient alias was removed in the v3.8 clean break.

    Accessing it from either module path must now fail rather than silently
    resolve to GatewayClient.
    """

    def test_alias_removed_from_client_module(self):
        import equser.api.client as api_client
        with pytest.raises(AttributeError):
            _ = api_client.SynapseClient

    def test_alias_removed_from_package(self):
        with pytest.raises(ImportError):
            from equser.api import SynapseClient  # noqa: F401


@pytest.mark.skipif(not HAS_WEBSOCKET, reason="websocket-client not installed")
class TestStreaming:
    def test_module_importable(self):
        from equser.api.streaming import connect_cpow_stream, connect_spectral_stream
        assert callable(connect_cpow_stream)
        assert callable(connect_spectral_stream)

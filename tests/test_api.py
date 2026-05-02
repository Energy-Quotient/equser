"""Tests for equser.api modules.

Requires requests (``[analysis]`` extra). HTTP calls are tested via
construction/URL building only (no actual network calls).
"""

import pytest

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

pytestmark = pytest.mark.skipif(not HAS_REQUESTS, reason="requests not installed")


class TestCoherenceClient:
    def test_default_url(self):
        from equser.api.client import CoherenceClient
        client = CoherenceClient()
        assert client.base_url == 'http://localhost:8080'

    def test_custom_url(self):
        from equser.api.client import CoherenceClient
        client = CoherenceClient('http://192.168.10.1:8080/')
        assert client.base_url == 'http://192.168.10.1:8080'

    def test_custom_timeout(self):
        from equser.api.client import CoherenceClient
        client = CoherenceClient(timeout=120)
        assert client.timeout == 120

    def test_url_trailing_slash_stripped(self):
        from equser.api.client import CoherenceClient
        client = CoherenceClient('http://host:8080///')
        assert not client.base_url.endswith('/')


class TestSynapseClientAlias:
    """Regression coverage for the backward-compatible SynapseClient alias.

    SynapseClient was renamed to CoherenceClient when the gateway software
    rebranded from EQ Synapse / EQ Watch to EQ Coherence™. The old name is
    preserved as a module-level alias so existing user code keeps working.
    """

    def test_alias_is_coherence_client(self):
        from equser.api.client import CoherenceClient, SynapseClient
        assert SynapseClient is CoherenceClient

    def test_alias_constructible(self):
        from equser.api.client import SynapseClient
        client = SynapseClient('http://192.168.10.1:8080')
        assert client.base_url == 'http://192.168.10.1:8080'

    def test_alias_imports_from_package(self):
        from equser.api import CoherenceClient, SynapseClient
        assert SynapseClient is CoherenceClient


class TestStreaming:
    def test_module_importable(self):
        from equser.api.streaming import connect_cpow_stream, connect_spectral_stream
        assert callable(connect_cpow_stream)
        assert callable(connect_spectral_stream)

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


class TestGatewayClient:
    def test_default_url(self):
        from equser.api.client import GatewayClient
        client = GatewayClient()
        assert client.base_url == 'http://localhost:8080'

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


class TestSynapseClientAlias:
    """Regression coverage for the deprecated SynapseClient alias.

    SynapseClient was the original class name from the EQ Synapse / EQ Watch
    era. The class is now named GatewayClient (addresses one EQ gateway over
    REST). SynapseClient is preserved as a deprecated module-level alias so
    existing user code keeps working; importing it emits a DeprecationWarning
    so users see the migration signal.
    """

    def test_alias_emits_deprecation_warning_on_client_module(self):
        import warnings
        import equser.api.client as api_client
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            cls = api_client.__getattr__('SynapseClient')
        assert cls is api_client.GatewayClient
        assert any(
            issubclass(w.category, DeprecationWarning) and 'SynapseClient' in str(w.message)
            for w in caught
        ), "Importing SynapseClient should emit a DeprecationWarning"

    def test_alias_emits_deprecation_warning_on_package(self):
        import warnings
        import equser.api as api
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            cls = api.__getattr__('SynapseClient')
        assert cls is api.GatewayClient
        assert any(
            issubclass(w.category, DeprecationWarning) and 'SynapseClient' in str(w.message)
            for w in caught
        ), "Importing SynapseClient from equser.api should emit a DeprecationWarning"

    def test_alias_is_gateway_client(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from equser.api.client import GatewayClient, SynapseClient
        assert SynapseClient is GatewayClient

    def test_alias_constructible(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from equser.api.client import SynapseClient
        client = SynapseClient('http://192.168.10.1:8080')
        assert client.base_url == 'http://192.168.10.1:8080'

    def test_alias_imports_from_package(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from equser.api import GatewayClient, SynapseClient
        assert SynapseClient is GatewayClient

    def test_alias_unknown_attribute_raises(self):
        import equser.api.client as api_client
        try:
            _ = api_client.NotAThing
        except AttributeError as e:
            assert 'NotAThing' in str(e)
        else:
            raise AssertionError("__getattr__ should raise AttributeError for unknown names")


class TestStreaming:
    def test_module_importable(self):
        from equser.api.streaming import connect_cpow_stream, connect_spectral_stream
        assert callable(connect_cpow_stream)
        assert callable(connect_spectral_stream)

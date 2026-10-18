"""Tests for equser.api modules.

Requires requests (``[analysis]`` extra). No test makes a network call: the
request helpers (``get_arrow``, ``query_sql``) are stubbed where HTTP is exercised.
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


def _cpow_chunk(ts, channels=('VA', 'VB', 'VC', 'IA', 'IB', 'IC', 'IN')):
    import pyarrow as pa
    cols = {'ts': pa.array(ts, pa.int64())}
    cols.update({c: pa.array([1.0] * len(ts), pa.float32()) for c in channels})
    return pa.table(cols).replace_schema_metadata({'cycle_starts': '[]'})


class TestGetCpowWindow:
    """get_cpow_window with the HTTP layer (get_arrow) stubbed."""

    def _client(self, monkeypatch, responder):
        from equser.api.client import GatewayClient
        client = GatewayClient('http://gw')
        calls = []

        def fake_get_arrow(endpoint, params=None):
            calls.append((endpoint, params))
            return responder(params)

        monkeypatch.setattr(client, '_get_arrow', fake_get_arrow)
        return client, calls

    def test_chunks_iso_times_and_sort(self, monkeypatch):
        # Return chunks newest-first content to prove the result is sorted by ts.
        def responder(params):
            base = int(params['start_time'][17:19]) * 10
            return _cpow_chunk([base + 2, base + 1])

        client, calls = self._client(monkeypatch, responder)
        t = client.get_cpow_window('default', 0, 40, chunk_s=15)

        z = '1970-01-01T00:00:{:02d}.000000Z'.format
        assert [c[1] for c in calls] == [
            {'start_time': z(0), 'end_time': z(15)},
            {'start_time': z(15), 'end_time': z(30)},
            {'start_time': z(30), 'end_time': z(40)},
        ]
        assert all(c[0] == '/api/v1/devices/default/cpow/data' for c in calls)
        assert t['ts'].to_pylist() == [1, 2, 151, 152, 301, 302]
        assert t.schema.metadata is None

    def test_datetime_bounds(self, monkeypatch):
        from datetime import datetime, timedelta, timezone
        client, calls = self._client(monkeypatch, lambda p: _cpow_chunk([1]))
        start = datetime(2026, 10, 17, 1, 2, 3, 456789, tzinfo=timezone(timedelta(hours=-10)))
        client.get_cpow_window('default', start, start + timedelta(seconds=2))
        assert calls == [('/api/v1/devices/default/cpow/data', {
            'start_time': '2026-10-17T11:02:03.456789Z',
            'end_time': '2026-10-17T11:02:05.456789Z',
        })]

    def test_channel_selection(self, monkeypatch):
        client, _ = self._client(monkeypatch, lambda p: _cpow_chunk([1, 2]))
        t = client.get_cpow_window('default', 0, 1, channels=['IA', 'VA'])
        assert t.column_names == ['ts', 'IA', 'VA']

    def test_missing_channel(self, monkeypatch):
        client, _ = self._client(monkeypatch, lambda p: _cpow_chunk([1], channels=('VA', 'IA')))
        with pytest.raises(ValueError, match=r"\['IN'\]"):
            client.get_cpow_window('default', 0, 1, channels=['VA', 'IN'])

    def test_empty_window(self, monkeypatch):
        client, calls = self._client(monkeypatch, lambda p: _cpow_chunk([]))
        with pytest.raises(ValueError, match='No CPOW data'):
            client.get_cpow_window('default', 0, 20, chunk_s=15)
        assert len(calls) == 2

    @staticmethod
    def _http_error(status, text='boom'):
        import requests
        resp = requests.Response()
        resp.status_code = status
        resp._content = text.encode()
        return requests.HTTPError(response=resp)

    def test_server_error_retried_once(self, monkeypatch):
        import equser.api.client as mod
        monkeypatch.setattr(mod, 'CPOW_RETRY_DELAY_S', 0)
        state = {'n': 0}

        def responder(params):
            state['n'] += 1
            if state['n'] == 1:
                raise self._http_error(500)
            return _cpow_chunk([1, 2])

        client, calls = self._client(monkeypatch, responder)
        t = client.get_cpow_window('default', 0, 1)
        assert len(calls) == 2 and t.num_rows == 2

    def test_persistent_server_error_names_cause(self, monkeypatch):
        import equser.api.client as mod
        monkeypatch.setattr(mod, 'CPOW_RETRY_DELAY_S', 0)

        def responder(params):
            raise self._http_error(500, 'No magic bytes found at end of file')

        client, calls = self._client(monkeypatch, responder)
        with pytest.raises(RuntimeError, match='No magic bytes'):
            client.get_cpow_window('default', 0, 1)
        assert len(calls) == 2

    def test_client_error_not_retried(self, monkeypatch):
        import requests

        def responder(params):
            raise self._http_error(404)

        client, calls = self._client(monkeypatch, responder)
        with pytest.raises(requests.HTTPError):
            client.get_cpow_window('default', 0, 1)
        assert len(calls) == 1

    def test_bad_bounds(self, monkeypatch):
        client, calls = self._client(monkeypatch, lambda p: _cpow_chunk([1]))
        with pytest.raises(ValueError):
            client.get_cpow_window('default', 10, 10)
        with pytest.raises(ValueError):
            client.get_cpow_window('default', 0, 10, chunk_s=0)
        assert calls == []


class TestGetCpowScales:
    """get_cpow_scales with the SQL endpoint (query_sql) stubbed."""

    NEWEST = '/data/cpow/20261017_120100.parquet'
    SECOND = '/data/cpow/20261017_120000.parquet'

    def _client(self, monkeypatch, files, metadata):
        import base64

        import pyarrow as pa

        from equser.api.client import GatewayClient

        client = GatewayClient('http://gw')
        queries = []

        def fake_query_sql(query, device_id=None, limit=None):
            queries.append((query, device_id))
            if 'glob(' in query:
                return pa.table({'file': pa.array(files, pa.string())})
            if metadata is None:
                return pa.table({'v': pa.array([], pa.string())})
            schema = pa.schema([('VA', pa.int32())], metadata=metadata)
            encoded = base64.b64encode(schema.serialize().to_pybytes()).decode()
            return pa.table({'v': [encoded]})

        monkeypatch.setattr(client, 'query_sql', fake_query_sql)
        return client, queries

    def test_reads_second_newest_file(self, monkeypatch):
        meta = {'vscale': '0.0003', 'iscale': '1.4e-05', 'gateway_id': 'EQG-TEST',
                'schema_version': '3'}
        client, queries = self._client(monkeypatch, [self.NEWEST, self.SECOND], meta)
        scales = client.get_cpow_scales()

        assert 'ORDER BY file DESC LIMIT 2' in queries[0][0]
        assert f"parquet_kv_metadata('{self.SECOND}')" in queries[1][0]
        assert all(q[1] == 'default' for q in queries)
        assert scales == {'vscale': 0.0003, 'iscale': 1.4e-05, 'gateway_id': 'EQG-TEST',
                          'schema_version': '3', 'source_file': self.SECOND}

    def test_needs_two_files(self, monkeypatch):
        client, _ = self._client(monkeypatch, [self.NEWEST], {'vscale': '1', 'iscale': '1'})
        with pytest.raises(RuntimeError, match='at least two'):
            client.get_cpow_scales()

    def test_no_arrow_schema(self, monkeypatch):
        client, _ = self._client(monkeypatch, [self.NEWEST, self.SECOND], None)
        with pytest.raises(RuntimeError, match='No Arrow schema'):
            client.get_cpow_scales()

    def test_missing_scale_keys(self, monkeypatch):
        client, _ = self._client(monkeypatch, [self.NEWEST, self.SECOND], {'vscale': '1'})
        with pytest.raises(RuntimeError, match='iscale'):
            client.get_cpow_scales()

"""REST API client for EQ gateways (running EQ Coherence™ software).

Requires the ``[analysis]`` extra::

    pip install equser[analysis]
"""

import base64
import math
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import pyarrow as pa
import pyarrow.ipc as ipc
import requests

# The gateway's nginx serves the API under /api on the normal HTTP port (it
# proxies to the backend on :8080 internally). Default to the plain host so
# clients never need port 8080 opened.
DEFAULT_GATEWAY_URL = "http://localhost"

# The CPOW data endpoint caps one response near 20 s (~640k rows at 32 kHz), so
# longer windows are fetched in chunks no larger than this.
DEFAULT_CPOW_CHUNK_S = 15.0

# Where the gateway writes CPOW Parquet files (read by get_cpow_scales via SQL).
CPOW_DATA_GLOB = '/var/lib/eq-coherence/data/cpow/*.parquet'


def _to_epoch_s(t: float | datetime) -> float:
    """Convert epoch seconds or a datetime to epoch seconds.

    A naive datetime is taken as UTC.
    """
    if isinstance(t, datetime):
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return t.timestamp()
    return float(t)


def _iso_utc(epoch_s: float) -> str:
    """Format epoch seconds as ISO-8601 UTC with microseconds and a ``Z`` suffix."""
    return datetime.fromtimestamp(epoch_s, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


class GatewayClient:
    """Client for the EQ gateway REST API (provided by EQ Coherence™ software).

    Provides typed access to device listing, power monitor data, CPOW data,
    events, and SQL queries on a single gateway.

    Args:
        gateway_url: Base URL of the gateway (default: http://localhost).
        timeout: Default request timeout in seconds (default: 60).

    Example::

        client = GatewayClient('http://192.168.10.1')
        devices = client.list_devices()
        table = client.get_pmon_data(devices[0]['id'])
    """

    def __init__(self, gateway_url: str = DEFAULT_GATEWAY_URL, timeout: int = 60):
        self.base_url = gateway_url.rstrip('/')
        self.timeout = timeout

    def get_arrow(self, endpoint: str, params: dict[str, Any] | None = None) -> pa.Table:
        """Fetch Arrow IPC data from a REST endpoint.

        Args:
            endpoint: API path (e.g. ``'/api/v1/devices/wave-001/pmon/data'``).
            params: Optional query parameters.

        Returns:
            PyArrow Table with the response data.

        Raises:
            requests.HTTPError: On non-2xx response.
            RuntimeError: If the response cannot be decoded as Arrow IPC.
        """
        url = self.base_url + endpoint
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        reader = ipc.open_stream(resp.content)
        return reader.read_all()

    # Backward-compatible alias
    _get_arrow = get_arrow

    def list_devices(self) -> list[dict[str, Any]]:
        """List all registered devices.

        Returns:
            List of device objects (JSON).
        """
        url = self.base_url + '/api/v1/devices'
        resp = requests.get(url, timeout=min(self.timeout, 30))
        resp.raise_for_status()
        return resp.json()['devices']

    def get_events(self, device_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch recent power quality events.

        Args:
            device_id: Optional filter by device.
            limit: Maximum events to return (default 100).

        Returns:
            List of event objects (JSON).
        """
        url = self.base_url + '/api/v1/events'
        params: dict[str, Any] = {"limit": limit}
        if device_id:
            params["device_id"] = device_id
        resp = requests.get(url, params=params, timeout=min(self.timeout, 30))
        resp.raise_for_status()
        return resp.json()['events']

    def get_pmon_data(self, device_id: str, **params: Any) -> pa.Table:
        """Fetch power monitor data for a device.

        Args:
            device_id: Device identifier.
            **params: Optional query parameters (start_time, end_time, metrics, limit).

        Returns:
            PyArrow Table with PMon data.
        """
        return self._get_arrow(f'/api/v1/devices/{device_id}/pmon/data', params or None)

    def get_cpow_data(self, device_id: str, **params: Any) -> pa.Table:
        """Fetch CPOW waveform data for a device.

        Args:
            device_id: Device identifier.
            **params: Optional query parameters (start_time, end_time, limit).

        Returns:
            PyArrow Table with CPOW data.
        """
        return self._get_arrow(f'/api/v1/devices/{device_id}/cpow/data', params or None)

    def get_cpow_window(
        self,
        device_id: str,
        start: float | datetime,
        end: float | datetime,
        channels: Sequence[str] | None = None,
        chunk_s: float = DEFAULT_CPOW_CHUNK_S,
    ) -> pa.Table:
        """Fetch a CPOW window of any length, in chunks the server will serve.

        The data endpoint caps one response near 20 s, so the window is
        requested as consecutive chunks of at most ``chunk_s`` seconds, which
        are concatenated and sorted by ``ts``. Values are in physical units
        (float32), as returned by :meth:`get_cpow_data`; per-chunk schema
        metadata is dropped.

        Args:
            device_id: Device identifier.
            start: Window start, as epoch seconds or a datetime (naive = UTC).
            end: Window end, as epoch seconds or a datetime (naive = UTC).
            channels: Optional channel names to keep (e.g. ``['VA', 'IA']``);
                ``ts`` is always included. Default: all columns.
            chunk_s: Maximum seconds per request (default 15).

        Returns:
            PyArrow Table sorted by ``ts``.

        Raises:
            ValueError: If ``end <= start``, ``chunk_s <= 0``, the window holds
                no data, or a requested channel is missing from the response.
        """
        t0, t1 = _to_epoch_s(start), _to_epoch_s(end)
        if t1 <= t0:
            raise ValueError(f"end ({t1}) must be after start ({t0})")
        if chunk_s <= 0:
            raise ValueError(f"chunk_s must be positive, got {chunk_s}")

        endpoint = f'/api/v1/devices/{device_id}/cpow/data'
        n_chunks = math.ceil((t1 - t0) / chunk_s)
        tables = []
        for i in range(n_chunks):
            a = t0 + i * chunk_s
            b = min(a + chunk_s, t1)
            chunk = self._get_arrow(endpoint, {'start_time': _iso_utc(a), 'end_time': _iso_utc(b)})
            if chunk.num_rows:
                tables.append(chunk.replace_schema_metadata(None))

        if not tables:
            raise ValueError(
                f"No CPOW data for device {device_id!r} between "
                f"{_iso_utc(t0)} and {_iso_utc(t1)}"
            )
        table = pa.concat_tables(tables)

        if channels is not None:
            missing = [c for c in channels if c not in table.column_names]
            if missing:
                raise ValueError(
                    f"CPOW channel(s) {missing} not in response; "
                    f"available: {table.column_names}"
                )
            table = table.select(['ts'] + [c for c in channels if c != 'ts'])

        return table.sort_by('ts')

    def get_cpow_scales(self, device_id: str = 'default') -> dict[str, Any]:
        """Read the CPOW scale factors the gateway stores with its Parquet files.

        :meth:`get_cpow_data` returns physical units without ``vscale`` or
        ``iscale``, so this reads them through the SQL endpoint from the Arrow
        schema embedded in the second-newest CPOW file (the newest may still be
        open and lack its Parquet footer). For files that store int32 counts,
        dividing the physical values by the scale recovers those counts.

        Args:
            device_id: Device ID context for the SQL queries (default ``'default'``).

        Returns:
            The file's Arrow schema metadata as a ``str -> str`` dict, with
            ``vscale`` and ``iscale`` converted to float. Includes
            ``gateway_id`` and ``schema_version`` when the file carries them,
            plus ``source_file`` (the gateway path the metadata came from).

        Raises:
            RuntimeError: If fewer than two CPOW files exist, the file carries
                no Arrow schema, or ``vscale``/``iscale`` are absent.
        """
        files = self.query_sql(
            f"SELECT file FROM glob('{CPOW_DATA_GLOB}') ORDER BY file DESC LIMIT 2",
            device_id=device_id,
        )
        if files.num_rows < 2:
            raise RuntimeError(
                f"Need at least two CPOW files to read scales (the newest may still be "
                f"open); found {files.num_rows}"
            )
        source_file = files['file'][1].as_py()

        quoted = source_file.replace("'", "''")
        kv = self.query_sql(
            f"SELECT decode(value) AS v FROM parquet_kv_metadata('{quoted}') "
            f"WHERE decode(key)='ARROW:schema'",
            device_id=device_id,
        )
        if kv.num_rows == 0:
            raise RuntimeError(f"No Arrow schema in CPOW file metadata: {source_file}")

        schema = ipc.read_schema(pa.py_buffer(base64.b64decode(kv['v'][0].as_py())))
        meta = {k.decode(): v.decode() for k, v in (schema.metadata or {}).items()}
        missing = [k for k in ('vscale', 'iscale') if k not in meta]
        if missing:
            raise RuntimeError(f"CPOW file {source_file} lacks scale metadata: {missing}")

        result: dict[str, Any] = dict(meta)
        result['vscale'] = float(meta['vscale'])
        result['iscale'] = float(meta['iscale'])
        result['source_file'] = source_file
        return result

    def query_sql(
        self, query: str, device_id: str | None = None, limit: int | None = None
    ) -> pa.Table:
        """Execute a SELECT query via the SQL endpoint.

        Args:
            query: SQL SELECT statement (only SELECT is allowed by the server).
            device_id: Optional device ID context for the query.
            limit: Optional row limit (server default is 30).

        Returns:
            PyArrow Table with the query result.

        Note:
            The server returns the result as Arrow IPC (same wire format as the
            data endpoints), so this decodes it exactly like ``get_arrow``.
        """
        url = self.base_url + '/api/v1/query/sql'
        body: dict[str, Any] = {"query": query}
        if device_id:
            body["device_id"] = device_id
        if limit is not None:
            body["limit"] = limit
        resp = requests.post(url, json=body, timeout=self.timeout)
        resp.raise_for_status()
        return ipc.open_stream(resp.content).read_all()

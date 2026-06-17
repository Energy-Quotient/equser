"""REST API client for EQ gateways (running EQ Coherence™ software).

Requires the ``[analysis]`` extra::

    pip install equser[analysis]
"""

from typing import Any

import pyarrow as pa
import pyarrow.ipc as ipc
import requests

# The gateway's nginx serves the API under /api on the normal HTTP port (it
# proxies to the backend on :8080 internally). Default to the plain host so
# clients never need port 8080 opened.
DEFAULT_GATEWAY_URL = "http://localhost"


class GatewayClient:
    """Client for the EQ gateway REST API (provided by EQ Coherence™ software at port 8080).

    Provides typed access to device listing, power monitor data, CPOW data,
    events, and SQL queries on a single gateway. For server-side cross-site
    queries against the aggregated datalake, use a future ``DatalakeClient``
    (not yet implemented).

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

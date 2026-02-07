"""Gateway REST API client and WebSocket streaming.

Requires the ``[analysis]`` extra (requests, websocket-client)::

    pip install equser[analysis]

Usage::

    from equser.api import SynapseClient

    client = SynapseClient()
    devices = client.list_devices()
    table = client.get_pmon_data('wave-001')
"""

try:
    from equser.api.client import SynapseClient
    from equser.api.streaming import connect_cpow_stream, connect_spectral_stream

    _has_api = True
except ImportError:
    _has_api = False

__all__ = []

if _has_api:
    __all__.extend(['SynapseClient', 'connect_cpow_stream', 'connect_spectral_stream'])

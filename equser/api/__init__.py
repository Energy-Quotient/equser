"""Gateway REST API client and WebSocket streaming.

Requires the ``[analysis]`` extra (requests, websocket-client)::

    pip install equser[analysis]

Usage::

    from equser.api import CoherenceClient

    client = CoherenceClient()
    devices = client.list_devices()
    table = client.get_pmon_data('wave-001')

(``SynapseClient`` is preserved as a backward-compatible alias for
``CoherenceClient``; existing user code continues to work without
modification.)
"""

try:
    from equser.api.client import CoherenceClient, SynapseClient
    from equser.api.streaming import connect_cpow_stream, connect_spectral_stream

    _has_api = True
except ImportError:
    _has_api = False

__all__ = []

if _has_api:
    __all__.extend(
        ['CoherenceClient', 'SynapseClient', 'connect_cpow_stream', 'connect_spectral_stream']
    )

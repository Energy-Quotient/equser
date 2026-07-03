"""Gateway REST API client and WebSocket streaming.

Requires the ``[analysis]`` extra (requests, websocket-client)::

    pip install equser[analysis]

Usage::

    from equser.api import GatewayClient

    client = GatewayClient()
    devices = client.list_devices()
    table = client.get_pmon_data('wave-001')
"""

try:
    from equser.api.client import GatewayClient  # noqa: F401
    from equser.api.streaming import (  # noqa: F401
        connect_cpow_stream,
        connect_spectral_stream,
    )

    _has_api = True
except ImportError:
    _has_api = False

__all__ = []

if _has_api:
    __all__.extend(['GatewayClient', 'connect_cpow_stream', 'connect_spectral_stream'])

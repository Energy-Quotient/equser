"""Gateway REST API client and WebSocket streaming.

Requires the ``[analysis]`` extra (requests, websocket-client)::

    pip install equser[analysis]

Usage::

    from equser.api import GatewayClient

    client = GatewayClient()
    devices = client.list_devices()
    table = client.get_pmon_data('wave-001')

(``SynapseClient`` is preserved as a deprecated backward-compatible alias
for ``GatewayClient``. Importing it emits a ``DeprecationWarning``; the
alias will be removed in a future release.)
"""

try:
    from equser.api.client import GatewayClient
    from equser.api.streaming import connect_cpow_stream, connect_spectral_stream

    _has_api = True
except ImportError:
    _has_api = False

__all__ = []

if _has_api:
    __all__.extend(
        ['GatewayClient', 'SynapseClient', 'connect_cpow_stream', 'connect_spectral_stream']
    )


# TODO(post-migration): remove this `__getattr__` hook and the SynapseClient
# entry in `__all__` above once known users (BlueField primarily) have
# migrated to GatewayClient. Mirror of the deprecation hook in
# `equser.api.client`; both are needed because users import from either
# module path.
def __getattr__(name):
    if name == 'SynapseClient' and _has_api:
        import warnings
        warnings.warn(
            "SynapseClient is deprecated and will be removed in a future "
            "release; use GatewayClient instead "
            "(`from equser.api import GatewayClient`).",
            DeprecationWarning,
            stacklevel=2,
        )
        from equser.api.client import GatewayClient as _GC
        return _GC
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""WebSocket streaming clients for real-time EQ gateway data.

Requires the ``[analysis]`` extra (websocket-client)::

    pip install equser[analysis]

CPOW WebSocket binary frames carry an 11-byte header before the Arrow
IPC payload — see ``equser.snapshot`` for the layout. Spectral WebSocket
binary frames are pure Arrow IPC streams (no header); per-window metadata
travels in the Arrow schema's key/value entries.
"""

import json
from collections.abc import Generator
from typing import Any

import pyarrow as pa
import pyarrow.ipc as ipc
import websocket

DEFAULT_GATEWAY_URL = "http://localhost"

CPOW_FRAME_HEADER_LEN = 11
CPOW_FRAME_MAGIC = 0x01


def connect_cpow_stream(
    gateway_url: str | None = None,
) -> Generator[Any | dict[str, Any], None, None]:
    """Connect to the CPOW waveform WebSocket and yield Arrow RecordBatches.

    Each binary message is an 11-byte cycle header followed by an Arrow
    IPC RecordBatch (~512 rows = 16 ms at 32 kHz). Text messages are
    JSON gap markers of the form ``{"type": "gap", "skipped_samples": N}``.

    Args:
        gateway_url: Base URL (default: http://localhost).
            The scheme is changed to ws:// automatically.

    Yields:
        ``pyarrow.RecordBatch`` for binary messages, or ``dict`` for gap markers.
    """
    base = (gateway_url or DEFAULT_GATEWAY_URL).rstrip('/')
    ws_url = base.replace('http://', 'ws://').replace('https://', 'wss://') + '/api/ws/cpow_stream'

    ws = websocket.create_connection(ws_url, timeout=10)
    try:
        while True:
            opcode, data = ws.recv_data()
            if opcode == websocket.ABNF.OPCODE_BINARY:
                if len(data) < CPOW_FRAME_HEADER_LEN or data[0] != CPOW_FRAME_MAGIC:
                    continue
                reader = ipc.open_stream(data[CPOW_FRAME_HEADER_LEN:])
                for batch in reader:
                    yield batch
            elif opcode == websocket.ABNF.OPCODE_TEXT:
                yield json.loads(data.decode('utf-8'))
            elif opcode == websocket.ABNF.OPCODE_PING:
                ws.pong(data)
            elif opcode in (websocket.ABNF.OPCODE_CLOSE,):
                break
    finally:
        ws.close()


SPECTRAL_CHANNELS = ('IA', 'VA', 'IB', 'VB', 'IC', 'VC', 'IN')


def connect_spectral_stream(
    channels: list[str] | tuple[str, ...] | str = ('VA', 'IA'),
    mode: str = 'cycle_aligned',
    cycles: int = 12,
    fft_size: int = 4096,
    freq_min: int = 0,
    freq_max: int = 3000,
    include_phase: bool = False,
    gateway_url: str | None = None,
) -> Generator[pa.Table | dict[str, Any], None, None]:
    """Connect to the spectral WebSocket and yield Arrow IPC spectral windows.

    The spectral stream is a broadcast consumer of the live CPOW feed (it is
    not per-device). Each binary message is one complete Arrow IPC stream
    holding the FFT magnitudes for the subscribed channels; per-window
    metadata (window_start_ts, fundamental_hz, THD, PLL state, ...) lives in
    the returned table's ``schema.metadata``. Text messages are JSON gap
    markers of the form ``{"type": "gap", "skipped_samples": N}``.

    Args:
        channels: Channel name(s) to analyze, from ``SPECTRAL_CHANNELS``
            (``IA, VA, IB, VB, IC, VC, IN``). Accepts a list/tuple or a
            comma-separated string. Names are upper-cased before sending.
        mode: ``'cycle_aligned'`` (one window per ``cycles`` PLL-locked
            cycles) or ``'fixed'`` (one window per ``fft_size`` samples,
            ignores PLL lock — use for off-nominal or unlocked data).
        cycles: Cycles per window in ``cycle_aligned`` mode (default 12).
        fft_size: Window size in ``fixed`` mode (default 4096, power of 2).
        freq_min: Minimum frequency in Hz (default 0).
        freq_max: Maximum frequency in Hz (default 3000).
        include_phase: Include per-bin phase columns alongside magnitudes.
        gateway_url: Base URL (default: http://localhost).
            The scheme is changed to ws:// automatically.

    Yields:
        ``pyarrow.Table`` for binary spectral windows, or ``dict`` for gap
        markers.
    """
    if isinstance(channels, str):
        channels = channels.split(',')
    chan_param = ','.join(c.strip().upper() for c in channels if c.strip())

    base = (gateway_url or DEFAULT_GATEWAY_URL).rstrip('/')
    query = [f'channels={chan_param}', f'mode={mode}']
    query.append(f'fft_size={fft_size}' if mode == 'fixed' else f'cycles={cycles}')
    query.append(f'freq_min={freq_min}')
    query.append(f'freq_max={freq_max}')
    query.append(f'include_phase={"true" if include_phase else "false"}')
    ws_url = (
        base.replace('http://', 'ws://').replace('https://', 'wss://')
        + '/api/ws/spectral?'
        + '&'.join(query)
    )

    ws = websocket.create_connection(ws_url, timeout=10)
    try:
        while True:
            opcode, data = ws.recv_data()
            if opcode == websocket.ABNF.OPCODE_BINARY:
                yield ipc.open_stream(data).read_all()
            elif opcode == websocket.ABNF.OPCODE_TEXT:
                yield json.loads(data.decode('utf-8'))
            elif opcode == websocket.ABNF.OPCODE_PING:
                ws.pong(data)
            elif opcode in (websocket.ABNF.OPCODE_CLOSE,):
                break
    finally:
        ws.close()

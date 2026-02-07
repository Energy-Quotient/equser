"""WebSocket streaming clients for real-time EQ Synapse data.

Requires the ``[analysis]`` extra (websocket-client)::

    pip install equser[analysis]
"""

import json
from typing import Any, Dict, Generator, Optional, Union

import pyarrow.ipc as ipc
import websocket

DEFAULT_GATEWAY_URL = "http://localhost:8080"


def connect_cpow_stream(
    gateway_url: Optional[str] = None,
) -> Generator[Union[Any, Dict[str, Any]], None, None]:
    """Connect to the CPOW waveform WebSocket and yield Arrow RecordBatches.

    Each binary message is an Arrow IPC RecordBatch containing ~512 rows
    (16 ms at 32 kHz). Text messages are JSON gap markers of the form
    ``{"type": "gap", "skipped_samples": N}``.

    Args:
        gateway_url: Base URL (default: http://localhost:8080).
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
                reader = ipc.open_stream(data)
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


def connect_spectral_stream(
    device_id: str,
    phase: str = 'va',
    fft_size: int = 4096,
    update_rate: float = 10.0,
    freq_min: int = 0,
    freq_max: int = 3000,
    gateway_url: Optional[str] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Connect to the spectral WebSocket and yield JSON frames.

    Args:
        device_id: Device identifier (required).
        phase: Channel to analyze ('va', 'vb', 'vc', 'ia', 'ib', 'ic').
        fft_size: FFT window size (default 4096, must be power of 2).
        update_rate: Spectral frames per second (default 10.0).
        freq_min: Minimum frequency in Hz (default 0).
        freq_max: Maximum frequency in Hz (default 3000).
        gateway_url: Base URL (default: http://localhost:8080).

    Yields:
        Parsed JSON spectral frame from the server.
    """
    base = (gateway_url or DEFAULT_GATEWAY_URL).rstrip('/')
    ws_url = (
        base.replace('http://', 'ws://').replace('https://', 'wss://')
        + f'/api/ws/spectral?device_id={device_id}'
        + f'&phase={phase}&fft_size={fft_size}&update_rate={update_rate}'
        + f'&freq_min={freq_min}&freq_max={freq_max}'
    )

    ws = websocket.create_connection(ws_url, timeout=10)
    try:
        while True:
            opcode, data = ws.recv_data()
            if opcode == websocket.ABNF.OPCODE_TEXT:
                yield json.loads(data.decode('utf-8'))
            elif opcode == websocket.ABNF.OPCODE_PING:
                ws.pong(data)
            elif opcode in (websocket.ABNF.OPCODE_CLOSE,):
                break
    finally:
        ws.close()

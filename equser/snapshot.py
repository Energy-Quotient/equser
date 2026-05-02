"""Capture live CPOW waveform data from an EQ gateway.

Connects to the gateway's CPOW WebSocket stream, collects a configurable
duration of waveform data, and writes the result to a timestamped parquet file.

Requires the ``[analysis]`` extra (websocket-client, pyarrow)::

    pip install equser[analysis]

Usage from CLI::

    equser snapshot
    equser snapshot --duration 10
    equser snapshot --host 192.168.1.100 --duration 5 --output capture.parquet

Wire format (`/api/ws/cpow_stream` binary frames)::

    Byte  0:     0x01  (frame magic — identifies a cycle frame)
    Byte  1:     pll_locked      (u8: 1=locked, 0=not locked)
    Bytes 2–5:   trigger_offset_ms (f32 little-endian)
    Bytes 6–9:   cycle_period_ms   (f32 little-endian)
    Byte  10:    cycle_count       (u8)
    Bytes 11+:   Arrow IPC stream payload (1+ record batches)

The 11-byte header is stripped before the Arrow IPC reader sees the
payload; otherwise pyarrow reads the magic byte as the start of a
metadata length and fails with "Invalid IPC stream: negative
continuation token".
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.ipc as ipc
import pyarrow.parquet as pq

SAMPLE_RATE = 32_000

CPOW_FRAME_HEADER_LEN = 11
CPOW_FRAME_MAGIC = 0x01


def capture(
    host: str = "localhost",
    port: int = 8080,
    duration: float = 5.0,
    output: Path | None = None,
) -> Path:
    """Capture live CPOW waveform data and save to a parquet file.

    Args:
        host: Gateway hostname or IP (default: ``'localhost'``).
        port: Gateway port (default: ``8080``).
        duration: Capture duration in seconds (default: ``5.0``).
        output: Output parquet file path. If ``None``, a timestamped
            filename is generated in the current directory.

    Returns:
        Path to the written parquet file.

    Raises:
        ImportError: If websocket-client is not installed.
        RuntimeError: If no data is received.
    """
    try:
        import websocket
    except ImportError as exc:
        raise ImportError(
            "websocket-client is required. Install with: pip install websocket-client"
        ) from exc

    if output is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output = Path(f"snapshot_{timestamp}.parquet")

    ws_url = f"ws://{host}:{port}/api/ws/cpow_stream"
    target_samples = int(duration * SAMPLE_RATE)

    print(f"Connecting to {ws_url}")
    ws = websocket.create_connection(ws_url, timeout=10)

    batches = []
    total_samples = 0
    gaps = 0
    start_time = time.time()

    print(f"Capturing {duration} seconds ({target_samples:,} samples)...")
    try:
        while total_samples < target_samples:
            opcode, data = ws.recv_data()

            if opcode == 0x02:  # Binary
                if len(data) < CPOW_FRAME_HEADER_LEN or data[0] != CPOW_FRAME_MAGIC:
                    # Skip frames we don't recognise (future header types).
                    continue
                reader = ipc.open_stream(data[CPOW_FRAME_HEADER_LEN:])
                for batch in reader:
                    batches.append(batch)
                    total_samples += len(batch)
            elif opcode == 0x01:  # Text
                msg = json.loads(data.decode("utf-8"))
                if msg.get("type") == "gap":
                    gaps += 1
                    skipped = msg.get("skipped_samples", 0)
                    print(f"  Gap: {skipped} samples skipped")
            elif opcode == 0x09:  # Ping
                ws.pong(data)
            elif opcode == 0x08:  # Close
                print("Server closed connection.")
                break
    except KeyboardInterrupt:
        print("\nCapture interrupted.")
    finally:
        ws.close()

    elapsed = time.time() - start_time

    if not batches:
        raise RuntimeError("No data received.")

    table = pa.Table.from_batches(batches)
    if len(table) > target_samples:
        table = table.slice(0, target_samples)

    pq.write_table(table, output)

    file_size = output.stat().st_size
    print("\nCapture complete:")
    print(f"  Samples:  {len(table):,} ({len(table) / SAMPLE_RATE:.2f} seconds)")
    print(f"  Batches:  {len(batches)}")
    if gaps:
        print(f"  Gaps:     {gaps}")
    print(f"  Elapsed:  {elapsed:.1f} seconds")
    print(f"  Output:   {output}")
    print(f"  Size:     {file_size / 1024:.0f} KB")

    return output


def main(argv=None):
    """CLI entry point for the snapshot subcommand."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Capture live CPOW waveform data to a parquet file.",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Gateway hostname or IP (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Gateway port (default: 8080)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Capture duration in seconds (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output parquet file path (default: snapshot_YYYYMMDD_HHMMSS.parquet)",
    )
    args = parser.parse_args(argv)
    capture(args.host, args.port, args.duration, args.output)


if __name__ == "__main__":
    main()

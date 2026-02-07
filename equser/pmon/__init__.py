"""Power monitoring module for EQ Wave sensors.

This module provides data acquisition and conversion capabilities for
power quality monitoring using EQ Wave hardware.

Always available:
    errors, schema, FIELD_DESCRIPTIONS

Requires ``[daq]`` extra:
    PowerMonitor, acquire, convert, convert_avro_to_parquet

CLI usage:
    equser pmon acquire [-c config.yaml]
    equser pmon convert file1.avro file2.avro [--remove]

Library usage:
    from equser.pmon import PowerMonitor, acquire, convert
"""

import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from typing import Optional, Sequence

from equser.core.paths import get_config_path
from equser.pmon.errors import ConfigurationError, ConnectionError, DataAcquisitionError
from equser.pmon.dataops import FIELD_DESCRIPTIONS, COLUMN_ENCODING

# DAQ classes require the [daq] extra (avro, fastavro)
try:
    from equser.pmon.daq import PowerMonitor, acquire
    from equser.pmon.dataops import convert, convert_avro_to_parquet
    _has_daq = True
except ImportError:
    _has_daq = False

__all__ = [
    'ConfigurationError',
    'ConnectionError',
    'DataAcquisitionError',
    'FIELD_DESCRIPTIONS',
    'COLUMN_ENCODING',
    'main',
]

if _has_daq:
    __all__.extend(['PowerMonitor', 'acquire', 'convert', 'convert_avro_to_parquet'])


def main(argv: Optional[Sequence[str]] = None, **kwargs) -> None:
    """Power quality monitoring CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])
        **kwargs: Additional arguments passed to ArgumentParser
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = ArgumentParser(
        description="Power quality monitoring tools for EQ Wave sensors",
        formatter_class=ArgumentDefaultsHelpFormatter,
        **kwargs
    )

    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Acquire command
    acquire_parser = subparsers.add_parser(
        'acquire',
        help="Acquire power, frequency, and RMS data from EQ Wave sensor",
        formatter_class=ArgumentDefaultsHelpFormatter
    )
    acquire_parser.add_argument(
        '-c', '--config',
        dest='config_path',
        default=None,
        help="Path to YAML configuration file (default: auto-detect)"
    )

    # Convert command
    convert_parser = subparsers.add_parser(
        'convert',
        help="Convert Avro file(s) to Parquet format",
        formatter_class=ArgumentDefaultsHelpFormatter
    )
    convert_parser.add_argument(
        'file_paths',
        nargs='+',
        help="Path(s) to Avro file(s). Glob patterns are accepted."
    )
    convert_parser.add_argument(
        '-c', '--config',
        dest='config_path',
        default=None,
        help="Path to YAML configuration file for compression settings"
    )
    convert_parser.add_argument(
        '--remove',
        dest='remove',
        action='store_true',
        help="Remove Avro file(s) after conversion"
    )

    # Try to enable argcomplete if available
    try:
        from argcomplete import autocomplete
        from argcomplete.completers import FilesCompleter
        # Set completers on existing actions (don't add new arguments)
        for action in acquire_parser._actions:
            if action.dest == 'config_path':
                action.completer = FilesCompleter(['yaml', 'yml'])
        for action in convert_parser._actions:
            if action.dest == 'file_paths':
                action.completer = FilesCompleter(['avro'])
            elif action.dest == 'config_path':
                action.completer = FilesCompleter(['yaml', 'yml'])
        autocomplete(parser)
    except ImportError:
        pass

    args = parser.parse_args(argv)

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return

    # Execute appropriate command
    if args.command == 'acquire':
        if not _has_daq:
            print("Error: Data acquisition requires the [daq] extra.")
            print("Install with: pip install equser[daq]")
            return
        acquire(args.config_path)
    elif args.command == 'convert':
        if not _has_daq:
            print("Error: Avro conversion requires the [daq] extra.")
            print("Install with: pip install equser[daq]")
            return
        convert(args.file_paths, args.remove, args.config_path)

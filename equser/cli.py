"""Command-line interface for equser.

Usage:
    equser pmon acquire [-c config.yaml]
    equser pmon convert file1.avro [--remove]
    equser plot data.parquet [--pmon|--cpow]
    equser snapshot [--host HOST] [--duration SEC] [--output FILE]
    equser notebooks list
    equser notebooks copy [--dest DIR] [--overwrite]
"""

import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point for equser.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success)
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = ArgumentParser(
        prog='equser',
        description="Power quality monitoring and analysis tools",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # pmon subcommand - delegates to equser.pmon
    pmon_parser = subparsers.add_parser(
        'pmon',
        help="Power monitoring commands (acquire, convert)",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    pmon_parser.add_argument('pmon_args', nargs='*', help="Arguments passed to pmon subcommand")

    # plot subcommand
    plot_parser = subparsers.add_parser(
        'plot',
        help="Plot data from Parquet file (requires equser[analysis])",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    plot_parser.add_argument('file', help="Path to Parquet file to plot")
    plot_parser.add_argument(
        '--pmon', action='store_true', help="Force interpretation as pmon data"
    )
    plot_parser.add_argument(
        '--cpow', action='store_true', help="Force interpretation as cpow data"
    )
    plot_parser.add_argument(
        '-o', '--output', help="Output file path (default: display interactively)"
    )

    # snapshot subcommand
    snapshot_parser = subparsers.add_parser(
        'snapshot',
        help="Capture live CPOW waveform data (requires equser[analysis])",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    snapshot_parser.add_argument(
        '--host',
        default='localhost',
        help="Gateway hostname or IP",
    )
    snapshot_parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help="Gateway port",
    )
    snapshot_parser.add_argument(
        '--duration',
        type=float,
        default=5.0,
        help="Capture duration in seconds",
    )
    snapshot_parser.add_argument(
        '--output',
        default=None,
        help="Output parquet file path",
    )

    # notebooks subcommand
    nb_parser = subparsers.add_parser(
        'notebooks',
        help="List or copy bundled reference notebooks",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    nb_sub = nb_parser.add_subparsers(dest='nb_action', help='Notebook commands')

    nb_sub.add_parser('list', help="List available notebooks")

    nb_copy = nb_sub.add_parser(
        'copy',
        help="Copy notebooks to a directory",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    nb_copy.add_argument(
        '--dest',
        default='.',
        help="Destination directory",
    )
    nb_copy.add_argument(
        '--overwrite',
        action='store_true',
        help="Overwrite existing files",
    )
    nb_copy.add_argument(
        '--category',
        choices=['tutorials', 'analysis'],
        default=None,
        help="Copy only a specific category",
    )

    # Try to enable argcomplete if available
    try:
        from argcomplete import autocomplete

        autocomplete(parser)
    except ImportError:
        pass

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == 'pmon':
        from equser.pmon import main as pmon_main

        return pmon_main(args.pmon_args) or 0

    if args.command == 'plot':
        return _handle_plot(args)

    if args.command == 'snapshot':
        return _handle_snapshot(args)

    if args.command == 'notebooks':
        return _handle_notebooks(args)

    return 0


def _handle_plot(args) -> int:
    """Handle the plot subcommand.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    try:
        from equser import plotting
    except ImportError:
        print("Error: Plotting requires equser[analysis] to be installed.")
        print("Install with: pip install 'equser[analysis]'")
        return 1

    from pathlib import Path

    import pyarrow.parquet as pq

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    # Auto-detect data type from schema if not specified
    data_type = None
    if args.pmon:
        data_type = 'pmon'
    elif args.cpow:
        data_type = 'cpow'
    else:
        # Try to detect from schema
        try:
            schema = pq.read_schema(file_path)
            field_names = [f.name for f in schema]
            if 'FREQ' in field_names and 'AVRMS' in field_names:
                data_type = 'pmon'
            elif 'VA' in field_names or 'IA' in field_names:
                data_type = 'cpow'
            else:
                print("Warning: Could not auto-detect data type. Use --pmon or --cpow.")
                return 1
        except Exception as e:
            print(f"Error reading file schema: {e}")
            return 1

    try:
        if data_type == 'pmon':
            plotter = plotting.PowerMonitorPlotter()
            plotter.plot_file(str(file_path), output_path=args.output)
        elif data_type == 'cpow':
            plotter = plotting.WaveformPlotter()
            plotter.plot_file(str(file_path), output_path=args.output)

        if not args.output:
            # Show interactive plot
            import matplotlib.pyplot as plt

            plt.show()

        return 0
    except Exception as e:
        print(f"Error plotting: {e}")
        return 1


def _handle_snapshot(args) -> int:
    """Handle the snapshot subcommand."""
    from pathlib import Path

    from equser.snapshot import capture

    output = Path(args.output) if args.output else None
    try:
        capture(args.host, args.port, args.duration, output)
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


def _handle_notebooks(args) -> int:
    """Handle the notebooks subcommand."""
    from equser.notebooks import copy_notebooks, list_notebooks

    if args.nb_action == 'list':
        notebooks = list_notebooks()
        if not notebooks:
            print("No notebooks found in package.")
            return 1
        for nb in notebooks:
            print(nb)
        return 0

    if args.nb_action == 'copy':
        copied = copy_notebooks(
            args.dest,
            overwrite=args.overwrite,
            category=args.category,
        )
        if copied:
            print(f"Copied {len(copied)} notebook(s) to {args.dest}")
            for p in copied:
                print(f"  {p}")
        else:
            print("No notebooks copied (files may already exist; use --overwrite to replace).")
        return 0

    # No sub-action given; print help
    print("Usage: equser notebooks {list,copy}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

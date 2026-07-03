"""Interactive Jupyter widgets for file selection and data exploration.

Requires the ``[jupyter]`` extra (ipywidgets)::

    pip install equser[jupyter]
"""

from datetime import datetime
from pathlib import Path


def create_file_selector(directory, pattern='*.parquet'):
    """Create a searchable file selector widget with file information.

    Displays a search box, file list, and detail pane. The returned widget
    has a ``get_selected()`` method that returns the currently selected
    :class:`~pathlib.Path`.

    Args:
        directory: Path to directory containing files.
        pattern: Glob pattern to match (default: ``'*.parquet'``).

    Returns:
        An ipywidgets VBox with a ``get_selected()`` helper method.

    Raises:
        ImportError: If ipywidgets is not installed.
    """
    try:
        import ipywidgets as widgets
    except ImportError as exc:
        raise ImportError(
            "create_file_selector requires ipywidgets.\nInstall with: pip install equser[jupyter]"
        ) from exc

    files = sorted(Path(directory).glob(pattern))

    def _file_options(file_list):
        return [(f.name, f) for f in file_list]

    search_box = widgets.Text(
        placeholder='Type to search files...',
        description='Search:',
        layout=widgets.Layout(width='500px'),
        style={'description_width': '60px'},
    )

    selector = widgets.Select(
        options=_file_options(files),
        description='Files:',
        layout=widgets.Layout(width='700px', height='250px'),
        style={'description_width': '60px'},
    )

    info_display = widgets.HTML(value='<i>Select a file to see details</i>')

    def _on_search(change):
        term = change['new'].lower()
        filtered = [f for f in files if term in f.name.lower()] if term else files
        selector.options = _file_options(filtered)
        info_display.value = '<i>Select a file to see details</i>'

    file_info_cache: dict = {}

    def _show_info(change):
        file_path = change['new']
        if not file_path:
            return
        if file_path in file_info_cache:
            info_display.value = file_info_cache[file_path]
            return
        try:
            stat = file_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            size_kb = stat.st_size / 1024
            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

            start_date_str = _parse_filename_date(file_path)

            info_html = (
                '<div style="background-color: #f0f0f0; padding: 10px; '
                'border-radius: 5px; margin-top: 10px;">'
                '<h4 style="margin-top: 0;">Selected File Details</h4>'
                f'<b>File Name:</b> {file_path.name}<br>'
                f'<b>Full Path:</b> <code>{file_path}</code><br>'
                f'<b>Size:</b> {size_mb:.2f} MB ({size_kb:.0f} KB)<br>'
                f'<b>Start Date:</b> {start_date_str}<br>'
                f'<b>Modified:</b> {mod_time}<br>'
                '</div>'
            )
            file_info_cache[file_path] = info_html
            info_display.value = info_html
        except OSError as exc:
            info_display.value = f"<div style='color: red;'>Error reading file info: {exc}</div>"

    clear_button = widgets.Button(
        description='Clear Search',
        button_style='',
        tooltip='Clear the search and show all files',
        layout=widgets.Layout(width='120px'),
    )

    def _clear(b):
        search_box.value = ''
        info_display.value = '<i>Select a file to see details</i>'

    search_box.observe(_on_search, names='value')
    selector.observe(_show_info, names='value')
    clear_button.on_click(_clear)

    count_display = widgets.HTML(value=f'<i>Found {len(files)} files</i>')

    def _update_count(change):
        term = change['new'].lower()
        if term:
            n = len([f for f in files if term in f.name.lower()])
            count_display.value = f'<i>Showing {n} of {len(files)} files</i>'
        else:
            count_display.value = f'<i>Found {len(files)} files</i>'

    search_box.observe(_update_count, names='value')

    file_selector = widgets.VBox(
        [
            widgets.HBox([search_box, clear_button]),
            count_display,
            selector,
            info_display,
        ]
    )

    def get_selected():
        return selector.value

    file_selector.get_selected = get_selected
    file_selector.selector = selector

    return file_selector


def _parse_filename_date(file_path: Path) -> str:
    """Try to parse a YYYYMMDD_HHMM timestamp from a parquet filename."""
    try:
        basename = file_path.stem
        if '_' in basename and len(basename.split('_')[0]) == 8:
            date_part = basename.split('_')[0]
            time_part = basename.split('_')[1] if len(basename.split('_')) > 1 else '0000'
            year = int(date_part[:4])
            month = int(date_part[4:6])
            day = int(date_part[6:8])
            hour = int(time_part[:2]) if len(time_part) >= 2 else 0
            minute = int(time_part[2:4]) if len(time_part) >= 4 else 0
            return datetime(year, month, day, hour, minute).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, IndexError):
        pass
    return "Could not parse from filename"

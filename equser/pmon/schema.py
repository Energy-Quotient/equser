"""Schema definitions for power monitor data.

Requires the ``[daq]`` extra (avro) for schema creation.
"""

from typing import List, Tuple

try:
    from avro.schema import RecordSchema
except ImportError:
    RecordSchema = None


def create_schema(num_phases: int) -> Tuple['RecordSchema', str, List[str]]:
    """Create Avro schema based on the sensor configuration.

    Args:
        num_phases: Number of phases (1-3) for data collection.

    Returns:
        Tuple of (schema, time_field_name, variable_names):

        - ``RecordSchema``: The Avro schema for the data
        - ``str``: Name of the time field ("time_us")
        - ``list[str]``: List of variable names in order

    Raises:
        ImportError: If avro package is not installed
        AssertionError: If num_phases is not between 1 and 3

    The schema includes:
    - Timestamp (microseconds since epoch)
    - Frequency
    - Per-phase measurements:
        - RMS voltage and current
        - Active power
        - Fundamental RMS voltage and current
        - Fundamental active and reactive power
    - Neutral current (RMS)
    """
    if RecordSchema is None:
        raise ImportError(
            "Schema creation requires the [daq] extra.\n"
            "Install with: pip install equser[daq]"
        )

    assert 1 <= num_phases <= 3, f"Invalid number of phases: {num_phases}"

    # Prefixes for phase-specific measurements
    phases = ['A'] + (['B'] if num_phases >= 2 else []) + (['C'] if num_phases == 3 else [])
    phases_plus_neutral = phases + ['N']
    apply_prefixes = lambda prefixes, base: [prefix + base for prefix in prefixes]

    time_name = "time_us"
    var_names = (
        ["FREQ"]
        + apply_prefixes(phases, "VRMS")  # RMS voltage
        + apply_prefixes(phases_plus_neutral, "IRMS")  # RMS current
        + apply_prefixes(phases, "WATT")   # Active power
        + apply_prefixes(phases, "FVRMS")  # Fundamental RMS voltage
        + apply_prefixes(phases, "FIRMS")  # Fundamental RMS current
        + apply_prefixes(phases, "FWATT")  # Fundamental active power
        + apply_prefixes(phases, "FVAR")   # Fundamental reactive power
    )

    # Create the schema in Avro format
    fields = [{"name": time_name, "type": "long"}] + \
             [{"name": name, "type": "float"} for name in var_names]

    schema = RecordSchema(
        name="PQSensor",
        namespace="power_monitor",
        fields=fields
    )

    return schema, time_name, var_names

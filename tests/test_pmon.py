"""Tests for equser.pmon modules (errors, schema, dataops)."""

import pytest

from equser.pmon.dataops import COLUMN_ENCODING, FIELD_DESCRIPTIONS
from equser.pmon.errors import ConfigurationError, DataAcquisitionError, SensorConnectionError

# --- errors ---

class TestErrorHierarchy:
    def test_connection_error_is_daq_error(self):
        assert issubclass(SensorConnectionError, DataAcquisitionError)

    def test_connection_error_is_oserror(self):
        assert issubclass(SensorConnectionError, OSError)

    def test_configuration_error_is_daq_error(self):
        assert issubclass(ConfigurationError, DataAcquisitionError)

    def test_configuration_error_is_value_error(self):
        assert issubclass(ConfigurationError, ValueError)

    def test_daq_error_is_runtime_error(self):
        assert issubclass(DataAcquisitionError, RuntimeError)


# --- schema ---

class TestCreateSchema:
    """Schema creation requires the [daq] extra (avro)."""

    @pytest.fixture(autouse=True)
    def _check_avro(self):
        try:
            from avro.schema import RecordSchema  # noqa: F401
        except ImportError:
            pytest.skip("avro not installed (requires [daq] extra)")

    def test_three_phases(self):
        from equser.pmon.schema import create_schema
        schema, time_name, var_names = create_schema(3)
        assert time_name == "time_us"
        assert "FREQ" in var_names
        assert "AVRMS" in var_names
        assert "BVRMS" in var_names
        assert "CVRMS" in var_names
        assert "NIRMS" in var_names

    def test_single_phase(self):
        from equser.pmon.schema import create_schema
        schema, time_name, var_names = create_schema(1)
        assert "AVRMS" in var_names
        assert "BVRMS" not in var_names
        assert "CVRMS" not in var_names
        assert "NIRMS" in var_names

    def test_two_phases(self):
        from equser.pmon.schema import create_schema
        schema, time_name, var_names = create_schema(2)
        assert "AVRMS" in var_names
        assert "BVRMS" in var_names
        assert "CVRMS" not in var_names

    def test_invalid_phases(self):
        from equser.pmon.schema import create_schema
        with pytest.raises(ValueError):
            create_schema(0)
        with pytest.raises(ValueError):
            create_schema(4)


# --- dataops ---

class TestFieldDescriptions:
    def test_time_us_present(self):
        assert 'time_us' in FIELD_DESCRIPTIONS

    def test_freq_present(self):
        assert 'FREQ' in FIELD_DESCRIPTIONS

    def test_phase_columns(self):
        for prefix in ['A', 'B', 'C']:
            assert f'{prefix}VRMS' in FIELD_DESCRIPTIONS
            assert f'{prefix}IRMS' in FIELD_DESCRIPTIONS
            assert f'{prefix}WATT' in FIELD_DESCRIPTIONS


class TestColumnEncoding:
    def test_time_us_delta(self):
        assert COLUMN_ENCODING['time_us'] == 'DELTA_BINARY_PACKED'

    def test_float_columns_byte_stream_split(self):
        assert COLUMN_ENCODING['FREQ'] == 'BYTE_STREAM_SPLIT'
        assert COLUMN_ENCODING['AVRMS'] == 'BYTE_STREAM_SPLIT'


class TestConvertAvroToParquet:
    """Avro conversion requires the [daq] extra (fastavro)."""

    def test_import_guard(self):
        """convert_avro_to_parquet raises ImportError when fastavro is missing."""
        # This test validates the guard works; if fastavro IS installed,
        # the function should work normally (tested elsewhere).
        from equser.pmon import dataops
        if dataops.fastavro is None:
            with pytest.raises(ImportError, match="daq"):
                dataops.convert_avro_to_parquet("/nonexistent.avro")

    def test_missing_file_returns_none(self):
        """Returns None for nonexistent files (when fastavro available)."""
        from equser.pmon import dataops
        if dataops.fastavro is None:
            pytest.skip("fastavro not installed")
        result = dataops.convert_avro_to_parquet("/definitely/not/a/real/file.avro")
        assert result is None

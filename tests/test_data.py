"""Tests for equser.data modules (cpow, pmon, timestamps)."""

from datetime import datetime

import numpy as np
import pyarrow as pa
import pytest

from equser.data.cpow import (
    CHANNELS,
    NEUTRAL_CT_RATIO,
    SAMPLE_RATE_HZ,
    get_cpow_scales,
    load_cpow,
    load_cpow_scaled,
)
from equser.data.pmon import FIELD_DESCRIPTIONS, load_pmon
from equser.data.timestamps import parse_filename_timestamp, parse_start_time

# --- cpow ---

class TestLoadCpow:
    def test_returns_table(self, sample_cpow_parquet):
        table = load_cpow(sample_cpow_parquet)
        assert isinstance(table, pa.Table)

    def test_columns(self, sample_cpow_parquet):
        table = load_cpow(sample_cpow_parquet)
        for ch in CHANNELS:
            assert ch in table.column_names

    def test_int32_dtype(self, sample_cpow_parquet):
        table = load_cpow(sample_cpow_parquet)
        assert table['VA'].type == pa.int32()

    def test_float_dtype(self, sample_cpow_float_parquet):
        table = load_cpow(sample_cpow_float_parquet)
        assert table['VA'].type == pa.float32()


class TestLoadCpowScaled:
    def test_int32_scaling(self, sample_cpow_parquet):
        result = load_cpow_scaled(sample_cpow_parquet)
        # Int32 data should be scaled - peak voltage should be ~170V (120*sqrt(2))
        assert result['vscale'] == pytest.approx(0.0001)
        assert result['iscale'] == pytest.approx(0.000005)
        # Check voltage is in reasonable physical range
        assert np.max(np.abs(result['VA'])) > 100  # Should be ~170V peak
        assert np.max(np.abs(result['VA'])) < 200

    def test_float_passthrough(self, sample_cpow_float_parquet):
        result = load_cpow_scaled(sample_cpow_float_parquet)
        assert result['vscale'] == 1.0
        assert result['iscale'] == 1.0
        # Float data already in physical units
        assert np.max(np.abs(result['VA'])) > 100

    def test_start_time_parsed(self, sample_cpow_parquet):
        result = load_cpow_scaled(sample_cpow_parquet)
        assert result['start_time'] is not None
        assert isinstance(result['start_time'], datetime)
        assert result['start_time'].year == 2025

    def test_start_time_none_for_float(self, sample_cpow_float_parquet):
        result = load_cpow_scaled(sample_cpow_float_parquet)
        assert result['start_time'] is None

    def test_sample_rate(self, sample_cpow_parquet):
        result = load_cpow_scaled(sample_cpow_parquet)
        assert result['sample_rate'] == SAMPLE_RATE_HZ

    def test_all_channels_present(self, sample_cpow_parquet):
        result = load_cpow_scaled(sample_cpow_parquet)
        for ch in CHANNELS:
            assert ch in result
            assert isinstance(result[ch], np.ndarray)

    def test_neutral_scaled_by_ct_ratio(self, sample_cpow_parquet):
        """IN must be scaled by iscale / NEUTRAL_CT_RATIO, not by iscale alone."""
        result = load_cpow_scaled(sample_cpow_parquet)
        raw_in = load_cpow(sample_cpow_parquet)['IN'].to_numpy().astype(np.float64)
        expected = raw_in * (result['iscale'] / NEUTRAL_CT_RATIO)
        np.testing.assert_allclose(result['IN'], expected)


class TestGetCpowScales:
    @staticmethod
    def _int_table():
        return pa.table({'VA': pa.array([1, 2, 3], type=pa.int32())})

    def test_int_defaults_to_neutral_ct_ratio(self):
        meta = {b'vscale': b'0.01', b'iscale': b'0.002'}
        vscale, iscale, neutral = get_cpow_scales(self._int_table(), meta)
        assert vscale == pytest.approx(0.01)
        assert iscale == pytest.approx(0.002)
        assert neutral == pytest.approx(0.002 / NEUTRAL_CT_RATIO)

    def test_metadata_overrides_divisor(self):
        # A file carrying a "special" neutral divisor overrides the default.
        meta = {b'iscale': b'0.002', b'neutral_ct_ratio': b'1'}
        _, iscale, neutral = get_cpow_scales(self._int_table(), meta)
        assert neutral == pytest.approx(iscale)

    def test_missing_scales_default_to_one(self):
        vscale, iscale, neutral = get_cpow_scales(self._int_table(), {})
        assert vscale == 1.0
        assert iscale == 1.0
        assert neutral == pytest.approx(1.0 / NEUTRAL_CT_RATIO)

    def test_float_table_is_prescaled(self):
        table = pa.table({'VA': pa.array([1.0, 2.0], type=pa.float32())})
        assert get_cpow_scales(table, None) == (1.0, 1.0, 1.0)


class TestConstants:
    def test_sample_rate(self):
        assert SAMPLE_RATE_HZ == 32_000

    def test_channels(self):
        assert CHANNELS == ['VA', 'VB', 'VC', 'IA', 'IB', 'IC', 'IN']

    def test_neutral_ct_ratio(self):
        assert NEUTRAL_CT_RATIO == 30


# --- pmon ---

class TestLoadPmon:
    def test_returns_table(self, sample_pmon_parquet):
        table = load_pmon(sample_pmon_parquet)
        assert isinstance(table, pa.Table)

    def test_has_expected_columns(self, sample_pmon_parquet):
        table = load_pmon(sample_pmon_parquet)
        assert 'time_us' in table.column_names
        assert 'FREQ' in table.column_names
        assert 'AVRMS' in table.column_names

    def test_row_count(self, sample_pmon_parquet):
        table = load_pmon(sample_pmon_parquet)
        assert len(table) == 100


class TestFieldDescriptions:
    def test_has_entries(self):
        assert len(FIELD_DESCRIPTIONS) > 0
        assert 'FREQ' in FIELD_DESCRIPTIONS
        assert 'time_us' in FIELD_DESCRIPTIONS

    def test_descriptions_are_strings(self):
        for key, value in FIELD_DESCRIPTIONS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


# --- timestamps ---

class TestParseStartTime:
    def test_nanosecond_precision(self):
        dt = parse_start_time('2025-06-23T07:50:56.662282101Z')
        assert dt.year == 2025
        assert dt.month == 6
        assert dt.day == 23
        assert dt.hour == 7
        assert dt.minute == 50
        assert dt.second == 56
        assert dt.microsecond == 662282

    def test_without_z_suffix(self):
        dt = parse_start_time('2025-06-23T07:50:56.123456')
        assert dt.microsecond == 123456

    def test_short_fractional(self):
        dt = parse_start_time('2025-01-01T00:00:00.1Z')
        assert dt.microsecond == 100000

    def test_six_digits(self):
        dt = parse_start_time('2025-01-01T12:30:45.999999Z')
        assert dt.microsecond == 999999

    def test_without_fractional_seconds(self):
        dt = parse_start_time('2025-06-23T07:50:56Z')
        assert dt == datetime(2025, 6, 23, 7, 50, 56)
        assert dt.microsecond == 0


class TestParseFilenameTimestamp:
    def test_pmon_format(self):
        dt = parse_filename_timestamp('20250623_0750.parquet')
        assert dt == datetime(2025, 6, 23, 7, 50)

    def test_cpow_format(self):
        dt = parse_filename_timestamp('20250623_075056.parquet')
        assert dt == datetime(2025, 6, 23, 7, 50, 56)

    def test_full_path(self):
        dt = parse_filename_timestamp('/var/lib/eq-coherence/data/pmon/20250623_0750.parquet')
        assert dt == datetime(2025, 6, 23, 7, 50)

    def test_no_match(self):
        assert parse_filename_timestamp('readme.txt') is None

    def test_invalid_date(self):
        assert parse_filename_timestamp('20251345_9999.parquet') is None

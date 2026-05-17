"""
Tests for fieldframe.fields.scaled — ScaledField class.
"""

import pytest
from fieldframe.fields.scaled import ScaledField


# ===========================================================================
# Construction
# ===========================================================================


class TestScaledFieldConstruction:
    def test_name_stored(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0, name="temp")
        assert sf.name == "temp"

    def test_name_is_none_by_default(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert sf.name is None

    def test_min_max_resolution_stored(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf.min_val == pytest.approx(-40.0)
        assert sf.max_val == pytest.approx(85.0)
        assert sf.resolution == pytest.approx(0.1)

    def test_default_is_min_val_when_not_provided(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf.write == pytest.approx(-40.0)

    def test_custom_default(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0, default=50.0)
        assert sf.write == pytest.approx(50.0)

    def test_read_is_none_initially(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert sf.read is None

    def test_read_raw_is_none_initially(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert sf.read_raw is None

    def test_min_ge_max_raises(self):
        with pytest.raises(ValueError, match="less than"):
            ScaledField(min_val=100.0, max_val=0.0, resolution=1.0)

    def test_min_equals_max_raises(self):
        with pytest.raises(ValueError):
            ScaledField(min_val=50.0, max_val=50.0, resolution=1.0)

    def test_resolution_zero_raises(self):
        with pytest.raises(ValueError, match="> 0"):
            ScaledField(min_val=0.0, max_val=100.0, resolution=0.0)

    def test_resolution_negative_raises(self):
        with pytest.raises(ValueError):
            ScaledField(min_val=0.0, max_val=100.0, resolution=-0.5)

    def test_resolution_too_coarse_raises(self):
        # range=0.1, resolution=1.0 → steps = round(0.1) = 0
        with pytest.raises(ValueError, match="coarse"):
            ScaledField(min_val=0.0, max_val=0.1, resolution=1.0)

    def test_integer_min_max_accepted(self):
        # int args should be stored as floats
        sf = ScaledField(min_val=0, max_val=100, resolution=1.0)
        assert isinstance(sf.min_val, float)
        assert isinstance(sf.max_val, float)


# ===========================================================================
# Bits and steps
# ===========================================================================


class TestScaledFieldBitsAndSteps:
    def test_temperature_steps(self):
        # round((85 − (−40)) / 0.1) = 1250
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf.steps == 1250

    def test_temperature_bits(self):
        # ceil(log2(1251)) = 11
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf.bits == 11

    def test_throttle_steps(self):
        # round((100 − 0) / 0.5) = 200
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=0.5)
        assert sf.steps == 200

    def test_throttle_bits(self):
        # ceil(log2(201)) = 8
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=0.5)
        assert sf.bits == 8

    def test_0_to_255_steps_and_bits(self):
        sf = ScaledField(min_val=0.0, max_val=255.0, resolution=1.0)
        assert sf.steps == 255
        assert sf.bits == 8  # ceil(log2(256)) = 8

    def test_0_to_1_single_step(self):
        sf = ScaledField(min_val=0.0, max_val=1.0, resolution=1.0)
        assert sf.steps == 1
        assert sf.bits == 1  # ceil(log2(2)) = 1

    def test_bits_property_matches_length(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf.bits == sf.length()

    def test_bits_at_least_1(self):
        sf = ScaledField(min_val=0.0, max_val=1.0, resolution=1.0)
        assert sf.bits >= 1

    def test_bits_is_int(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert isinstance(sf.bits, int)


# ===========================================================================
# write property
# ===========================================================================


class TestScaledFieldWriteProperty:
    def test_write_valid_midpoint(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        sf.write = 50.0
        assert sf.write == pytest.approx(50.0)

    def test_write_at_min(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        sf.write = -40.0
        assert sf.write == pytest.approx(-40.0)

    def test_write_at_max(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        sf.write = 85.0
        assert sf.write == pytest.approx(85.0)

    def test_write_below_min_raises(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        with pytest.raises(ValueError, match="out of range"):
            sf.write = -0.1

    def test_write_above_max_raises(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        with pytest.raises(ValueError, match="out of range"):
            sf.write = 100.1

    def test_write_wrong_type_raises_type_error(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        with pytest.raises(TypeError):
            sf.write = [50.0]

    def test_write_none_raises_type_error(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        with pytest.raises(TypeError):
            sf.write = None

    def test_write_int_accepted(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        sf.write = 50
        assert sf.write == pytest.approx(50.0)

    def test_write_string_converted(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        sf.write = "75.0"
        assert sf.write == pytest.approx(75.0)

    def test_write_invalid_string_raises(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        with pytest.raises(ValueError):
            sf.write = "not_a_float"

    def test_write_is_stored_as_float(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        sf.write = 50
        assert isinstance(sf.write, float)


# ===========================================================================
# _to_int / _to_float helpers
# ===========================================================================


class TestScaledFieldConversionHelpers:
    def test_to_int_at_min_val(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf._to_int(-40.0) == 0

    def test_to_int_at_max_val(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf._to_int(85.0) == 1250

    def test_to_int_midpoint(self):
        # (25 − (−40)) / 0.1 = 650
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf._to_int(25.0) == 650

    def test_to_int_clamped_below(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert sf._to_int(-999.0) == 0

    def test_to_int_clamped_above(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert sf._to_int(999.0) == 100

    def test_to_float_at_zero(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf._to_float(0) == pytest.approx(-40.0)

    def test_to_float_at_max_step(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf._to_float(1250) == pytest.approx(85.0)

    def test_to_float_midpoint(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        assert sf._to_float(650) == pytest.approx(25.0)

    def test_to_int_to_float_round_trip(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=0.5)
        for v in [0.0, 25.0, 50.0, 75.0, 100.0]:
            assert sf._to_float(sf._to_int(v)) == pytest.approx(v, abs=0.25)


# ===========================================================================
# _encode_bits / _decode_bits
# ===========================================================================


class TestScaledFieldEncodeDecode:
    def test_encode_min_val_is_all_zeros(self):
        sf = ScaledField(min_val=0.0, max_val=255.0, resolution=1.0)
        sf.write = 0.0
        assert sf._encode_bits("big") == "0" * 8

    def test_encode_known_temperature_25c(self):
        # wire_int = 650 = 0b01010001010 (11 bits)
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1, name="temp")
        sf.write = 25.0
        assert sf._encode_bits("big") == "01010001010"

    def test_encode_length_matches_bits(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        sf.write = 0.0
        assert len(sf._encode_bits("big")) == sf.bits

    def test_encode_only_bit_chars(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        sf.write = 42.0
        assert set(sf._encode_bits("big")) <= {"0", "1"}

    def test_decode_sets_read(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        sf.write = 0.0
        encoded = sf._encode_bits("big")

        recv = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert recv.read is None
        recv._decode_bits(encoded, "big")
        assert recv.read is not None

    def test_decode_sets_read_raw(self):
        sf = ScaledField(min_val=0.0, max_val=255.0, resolution=1.0)
        sf.write = 42.0
        encoded = sf._encode_bits("big")

        recv = ScaledField(min_val=0.0, max_val=255.0, resolution=1.0)
        recv._decode_bits(encoded, "big")
        assert recv.read_raw == 42

    def test_decode_returns_float(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        sf.write = 0.0
        encoded = sf._encode_bits("big")
        recv = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        result = recv._decode_bits(encoded, "big")
        assert isinstance(result, float)

    @pytest.mark.parametrize("value", [-40.0, -10.0, 0.0, 25.0, 50.5, 85.0])
    def test_round_trip_big_endian(self, value):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        sf.write = value
        encoded = sf._encode_bits("big")
        recv = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        decoded = recv._decode_bits(encoded, "big")
        assert decoded == pytest.approx(value, abs=0.05)

    def test_round_trip_little_endian(self):
        # Use a range that produces a 16-bit wire field (byte-aligned) so the
        # byte-swap is well-defined.  steps=65535 → bits=16.
        sf = ScaledField(min_val=0.0, max_val=655.35, resolution=0.01)
        assert sf.bits == 16
        sf.write = 327.67
        encoded = sf._encode_bits("little")
        recv = ScaledField(min_val=0.0, max_val=655.35, resolution=0.01)
        decoded = recv._decode_bits(encoded, "little")
        assert decoded == pytest.approx(327.67, abs=0.005)

    def test_big_endian_vs_little_differ_when_multibyte(self):
        # 11-bit field → 2 bytes needed → endian matters
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1)
        sf.write = 25.0
        big = sf._encode_bits("big")
        little = sf._encode_bits("little")
        assert big != little


# ===========================================================================
# Display
# ===========================================================================


class TestScaledFieldDisplay:
    def test_repr_contains_name(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0, name="throttle")
        assert "throttle" in repr(sf)

    def test_repr_contains_range(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1, name="temp")
        r = repr(sf)
        assert "-40.0" in r
        assert "85.0" in r

    def test_repr_contains_resolution(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=0.5, name="x")
        assert "0.5" in repr(sf)

    def test_repr_contains_bits(self):
        sf = ScaledField(min_val=-40.0, max_val=85.0, resolution=0.1, name="temp")
        assert "11" in repr(sf)

    def test_repr_contains_write_value(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0, name="x")
        sf.write = 42.0
        assert "42.0" in repr(sf)

    def test_str_contains_range(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0, name="x")
        s = str(sf)
        assert "0.0" in s
        assert "100.0" in s

    def test_str_shows_read_none_as_dash(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0, name="x")
        assert "—" in str(sf)

    def test_type_str_contains_scaled(self):
        sf = ScaledField(min_val=0.0, max_val=100.0, resolution=1.0)
        assert "scaled" in str(sf.type)

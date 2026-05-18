"""
fieldframe.types.float
~~~~~~~~~~~~~~~~~~~~~~

IEEE 754 floating-point type descriptor used by :class:`~fieldframe.fields.field.Field`.

Only three widths are valid — 16-bit (half), 32-bit (single), 64-bit (double) —
matching the three formats the Python :mod:`struct` module supports directly:

.. code-block:: python

    from fieldframe.types.float import float_type, single_type, double_type

    temperature = Field(name="temperature", type=float_type(32), default=0.0)
    latitude    = Field(name="latitude",    type=double_type(),  default=0.0)

Bit ordering and byte-swapping follow the same rules as :class:`~fieldframe.types.int.IntType`:
multi-byte fields are byte-swapped for little-endian messages; single-byte fields
(none exist for floats, but the rule is applied consistently) are not.

``min_value`` and ``max_value`` reflect the largest *finite* representable value
for the chosen width.  ``±inf`` and ``NaN`` are valid on the wire but are
rejected by :meth:`FloatType.validate` to prevent silent data corruption —
pass ``allow_special=True`` at construction if your protocol requires them.
"""

import math
import struct
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# struct format character for each supported width (big-endian prefix added at use)
_STRUCT_FMT: dict[int, str] = {16: "e", 32: "f", 64: "d"}


# Largest finite positive value for each width, derived from struct so there
# is no hard-coded magic number to maintain.
def _max_finite(bits: int) -> float:
    fmt = _STRUCT_FMT[bits]
    # Build the bit pattern for the largest finite value:
    # sign=0, all exponent bits 1 except the LSB, all mantissa bits 1.
    # Equivalent to the largest bytes that unpack without overflow.
    max_bytes = {
        16: b"\x7b\xff",  # 0x7BFF = 65504.0
        32: b"\x7f\x7f\xff\xff",  # 0x7F7FFFFF ≈ 3.4028e+38
        64: b"\x7f\xef\xff\xff\xff\xff\xff\xff",  # 0x7FEFFFFF… ≈ 1.7977e+308
    }
    return struct.unpack(f">{fmt}", max_bytes[bits])[0]


# ---------------------------------------------------------------------------
# Descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FloatType:
    """Immutable descriptor for an IEEE 754 floating-point field.

    Parameters
    ----------
    bits : int
        Width in bits.  Must be ``16``, ``32``, or ``64``.
    allow_special : bool
        When ``True``, :meth:`validate` accepts ``±inf`` and ``NaN``.
        Default ``False``.

    Raises
    ------
    ValueError
        If *bits* is not 16, 32, or 64.

    Examples
    --------
    >>> FloatType(bits=32)
    FloatType(float32  range=[-3.4028234663852886e+38, 3.4028234663852886e+38])
    >>> FloatType(bits=16)
    FloatType(float16  range=[-65504.0, 65504.0])
    """

    bits: int
    allow_special: bool = field(default=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if self.bits not in _STRUCT_FMT:
            raise ValueError(
                f"FloatType only supports 16, 32, or 64 bits; got {self.bits}"
            )

    # ------------------------------------------------------------------
    # Range helpers
    # ------------------------------------------------------------------

    @property
    def max_value(self) -> float:
        """Largest finite positive value representable by this type."""
        return _max_finite(self.bits)

    @property
    def min_value(self) -> float:
        """Largest finite negative value representable by this type."""
        return -_max_finite(self.bits)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, value: float) -> bool:
        """Check that *value* is representable by this type.

        Parameters
        ----------
        value : float or int
            The value to validate.  Plain ``int`` values are accepted and
            will be cast to ``float`` at encode time.

        Returns
        -------
        bool
            Always ``True`` when valid.

        Raises
        ------
        TypeError
            If *value* is not a ``float`` or ``int``.
        ValueError
            If *value* is ``NaN`` or ``±inf`` and ``allow_special`` is
            ``False``, or if *value* exceeds the representable range.
        """
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected float or int, got {type(value).__name__!r}")
        if math.isnan(value):
            if not self.allow_special:
                raise ValueError(
                    f"NaN is not allowed for {self} — "
                    f"construct with allow_special=True to permit it"
                )
            return True
        if math.isinf(value):
            if not self.allow_special:
                raise ValueError(
                    f"±inf is not allowed for {self} — "
                    f"construct with allow_special=True to permit it"
                )
            return True
        if not (self.min_value <= value <= self.max_value):
            raise ValueError(
                f"{value} overflows {self} "
                f"(range: [{self.min_value}, {self.max_value}])"
            )
        return True

    # ------------------------------------------------------------------
    # Encode / decode
    # ------------------------------------------------------------------

    def encode_bits(self, value: float, endian: str) -> str:
        """Encode *value* to a ``'0'``/``'1'`` string of length :attr:`bits`.

        Parameters
        ----------
        value : float or int
            Must already be validated.
        endian : {'big', 'little'}
            Multi-byte fields are byte-swapped for little-endian messages.

        Returns
        -------
        str
            Bit string of length :attr:`bits`.
        """
        fmt = _STRUCT_FMT[self.bits]
        raw_bytes = struct.pack(f">{fmt}", float(value))

        if endian == "little":
            raw_bytes = bytes(reversed(raw_bytes))

        return "".join(f"{byte:08b}" for byte in raw_bytes)

    def decode_bits(self, bit_str: str, endian: str) -> float:
        """Decode a bit string back to a float.

        Parameters
        ----------
        bit_str : str
            Exactly :attr:`bits` characters of ``'0'``/``'1'``.
        endian : {'big', 'little'}
            Multi-byte fields are byte-unswapped before interpretation.

        Returns
        -------
        float
            The decoded value.
        """
        fmt = _STRUCT_FMT[self.bits]

        # Convert bit string → bytes
        raw_bytes = bytes(int(bit_str[i : i + 8], 2) for i in range(0, len(bit_str), 8))

        if endian == "little":
            raw_bytes = bytes(reversed(raw_bytes))

        return struct.unpack(f">{fmt}", raw_bytes)[0]

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        """Short type name, e.g. ``float32``."""
        return f"float{self.bits}"

    def __repr__(self) -> str:
        """Detailed single-line representation showing range.

        Example::

            FloatType(float32  range=[-3.4028234663852886e+38, 3.4028234663852886e+38])
        """
        return f"FloatType({self!s:<8} range=[{self.min_value}, {self.max_value}])"


# ---------------------------------------------------------------------------
# Convenience factories
# ---------------------------------------------------------------------------


def float_type(bits: int, allow_special: bool = False) -> FloatType:
    """Create a :class:`FloatType` for the given bit width (16, 32, or 64).

    Parameters
    ----------
    bits : int
        Width in bits — must be ``16``, ``32``, or ``64``.
    allow_special : bool
        Pass ``True`` to permit ``±inf`` and ``NaN``.

    Examples
    --------
    >>> float_type(32)
    FloatType(float32  range=[-3.4028234663852886e+38, 3.4028234663852886e+38])
    """
    return FloatType(bits=bits, allow_special=allow_special)


def half_type(allow_special: bool = False) -> FloatType:
    """Create a 16-bit (half-precision) :class:`FloatType`.

    Range: ±65504.0

    Examples
    --------
    >>> half_type()
    FloatType(float16  range=[-65504.0, 65504.0])
    """
    return FloatType(bits=16, allow_special=allow_special)


def single_type(allow_special: bool = False) -> FloatType:
    """Create a 32-bit (single-precision) :class:`FloatType`.

    Examples
    --------
    >>> single_type()
    FloatType(float32  range=[-3.4028234663852886e+38, 3.4028234663852886e+38])
    """
    return FloatType(bits=32, allow_special=allow_special)


def double_type(allow_special: bool = False) -> FloatType:
    """Create a 64-bit (double-precision) :class:`FloatType`.

    Examples
    --------
    >>> double_type()
    FloatType(float64  range=[-1.7976931348623157e+308, 1.7976931348623157e+308])
    """
    return FloatType(bits=64, allow_special=allow_special)

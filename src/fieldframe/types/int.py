"""
fieldframe.types.int
~~~~~~~~~~~~~~~~~~~~

Integer type descriptors used by every field in fieldframe.

An :class:`IntType` captures the two things a binary integer field needs:
how many bits it occupies and whether it is signed.  It is immutable and
hashable, so the same descriptor can be shared safely across many fields.

Convenience factories :func:`int_type` and :func:`uint_type` cover the
common case:

.. code-block:: python

    from fieldframe.types.int import int_type, uint_type

    speed_type     = uint_type(8)   # 0 … 255
    heading_type   = int_type(16)   # -32 768 … 32 767
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntType:
    """Immutable descriptor for a fixed-width binary integer.

    Parameters
    ----------
    bits : int
        Width in bits.  Must be between 1 and 64 inclusive.
    signed : bool
        ``True`` for a two's-complement signed integer,
        ``False`` for an unsigned integer.

    Raises
    ------
    ValueError
        If *bits* is less than 1 or greater than 64.

    Examples
    --------
    >>> IntType(bits=8, signed=False)
    IntType(uint8  range=[0, 255])
    >>> IntType(bits=16, signed=True)
    IntType(int16  range=[-32768, 32767])
    """

    bits:   int
    signed: bool

    def __post_init__(self) -> None:
        if self.bits < 1:
            raise ValueError(f"bits must be >= 1, got {self.bits}")
        if self.bits > 64:
            raise ValueError(f"bits must be <= 64, got {self.bits}")

    # ------------------------------------------------------------------
    # Range helpers
    # ------------------------------------------------------------------

    @property
    def min_value(self) -> int:
        """Minimum representable value for this type."""
        return -(2 ** (self.bits - 1)) if self.signed else 0

    @property
    def max_value(self) -> int:
        """Maximum representable value for this type."""
        return (2 ** (self.bits - 1)) - 1 if self.signed else (2 ** self.bits) - 1

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, value: int) -> bool:
        """Check that *value* fits within this type.

        Parameters
        ----------
        value : int
            The value to validate.

        Returns
        -------
        bool
            Always ``True`` when the value is valid.

        Raises
        ------
        TypeError
            If *value* is not an :class:`int`.
        ValueError
            If *value* is outside ``[min_value, max_value]``.
        """
        if not isinstance(value, int):
            raise TypeError(
                f"Expected int, got {type(value).__name__!r}"
            )
        if not (self.min_value <= value <= self.max_value):
            raise ValueError(
                f"{value} is out of range for {self} "
                f"(valid range: [{self.min_value}, {self.max_value}])"
            )
        return True

    # ------------------------------------------------------------------
    # Encode / decode
    # ------------------------------------------------------------------

    def encode_bits(self, value: int, endian: str) -> str:
        """Encode *value* to a ``'0'``/``'1'`` string of length :attr:`bits`.

        Parameters
        ----------
        value : int
            Must already be validated (call :meth:`validate` first).
        endian : {'big', 'little'}
            Multi-byte fields are byte-swapped for little-endian; single-byte
            and sub-byte fields are never swapped.

        Returns
        -------
        str
            Bit string of length :attr:`bits`.
        """
        from bitarray.util import int2ba

        raw = int2ba(
            value,
            length=self.bits,
            endian="big",
            signed=self.signed,
        ).to01()

        if endian == "little" and self.bits > 8:
            chunks = [raw[i:i + 8] for i in range(0, len(raw), 8)]
            return "".join(reversed(chunks))

        return raw

    def decode_bits(self, bit_str: str, endian: str) -> int:
        """Decode a bit string back to an integer.

        Parameters
        ----------
        bit_str : str
            Exactly :attr:`bits` characters of ``'0'``/``'1'``.
        endian : {'big', 'little'}
            Multi-byte fields are byte-unswapped before interpretation.

        Returns
        -------
        int
            The decoded integer value.
        """
        from bitarray import bitarray
        from bitarray.util import ba2int

        if endian == "little" and len(bit_str) > 8:
            chunks = [bit_str[i:i + 8] for i in range(0, len(bit_str), 8)]
            bit_str = "".join(reversed(chunks))

        return ba2int(bitarray(bit_str), signed=self.signed)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        """Short type name, e.g. ``uint8`` or ``int16``."""
        prefix = "int" if self.signed else "uint"
        return f"{prefix}{self.bits}"

    def __repr__(self) -> str:
        """Detailed single-line representation showing range.

        Example::

            IntType(uint8  range=[0, 255])
        """
        return (
            f"IntType({self!s:<6} "
            f"range=[{self.min_value}, {self.max_value}])"
        )


# ---------------------------------------------------------------------------
# Convenience factories
# ---------------------------------------------------------------------------

def int_type(bits: int) -> IntType:
    """Create a signed two's-complement :class:`IntType`.

    Parameters
    ----------
    bits : int
        Width in bits (1–64).

    Returns
    -------
    IntType

    Examples
    --------
    >>> int_type(8)
    IntType(int8   range=[-128, 127])
    """
    return IntType(bits=bits, signed=True)


def uint_type(bits: int) -> IntType:
    """Create an unsigned :class:`IntType`.

    Parameters
    ----------
    bits : int
        Width in bits (1–64).

    Returns
    -------
    IntType

    Examples
    --------
    >>> uint_type(8)
    IntType(uint8  range=[0, 255])
    """
    return IntType(bits=bits, signed=False)
"""
fieldframe.types.string
~~~~~~~~~~~~~~~~~~~~~~~

Fixed-width string type descriptor used by :class:`~fieldframe.fields.field.Field`.

A :class:`StringType` occupies a fixed number of **bytes** on the wire.
Short strings are right-padded with a configurable pad character (default
``\\x00``); strings that encode to more bytes than the field allows raise
:exc:`ValueError` at assignment time.

.. code-block:: python

    from fieldframe.types.string import str_type, utf8_type

    class Packet(Message):
        label    = Field(name="label",    type=str_type(8),     default="")
        callsign = Field(name="callsign", type=ascii_type(6),   default="------")
        name     = Field(name="name",     type=utf8_type(32),   default="")

Endianness has no effect on string fields — bytes are always written and
read in left-to-right order, matching the way string data is conventionally
transmitted.

Pad stripping
-------------
On decode, trailing pad characters are stripped from the right.  If your
protocol uses space-padding instead of null-padding, pass ``pad=' '``:

.. code-block:: python

    padded = StringType(length=8, encoding="ascii", pad=" ")
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StringType:
    """Immutable descriptor for a fixed-width string field.

    Parameters
    ----------
    length : int
        Width of the field in **bytes**.  The bit width is ``length * 8``.
        Must be at least 1.
    encoding : str
        Python codec name used to encode/decode the string.
        Default ``'ascii'``.
    pad : str
        Single character used to pad short strings to the full field width.
        Must encode to exactly one byte under *encoding*.
        Default ``'\\x00'`` (null byte).

    Raises
    ------
    ValueError
        If *length* < 1, or if *pad* does not encode to a single byte.

    Examples
    --------
    >>> StringType(length=8)
    StringType(ascii  8 bytes  pad=\\x00)
    >>> StringType(length=16, encoding='utf-8', pad=' ')
    StringType(utf-8  16 bytes  pad= )
    """

    length: int
    encoding: str = "ascii"
    pad: str = "\x00"

    def __post_init__(self) -> None:
        if self.length < 1:
            raise ValueError(f"StringType length must be >= 1, got {self.length}")
        try:
            pad_bytes = self.pad.encode(self.encoding)
        except (UnicodeEncodeError, LookupError) as exc:
            raise ValueError(
                f"Pad character {self.pad!r} cannot be encoded as {self.encoding!r}: {exc}"
            ) from exc
        if len(pad_bytes) != 1:
            raise ValueError(
                f"Pad character {self.pad!r} must encode to exactly 1 byte "
                f"under {self.encoding!r}, got {len(pad_bytes)}"
            )

    # ------------------------------------------------------------------
    # Width helper (mirrors IntType.bits interface so Field works uniformly)
    # ------------------------------------------------------------------

    @property
    def bits(self) -> int:
        """Total field width in bits (``length * 8``)."""
        return self.length * 8

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, value: str) -> bool:
        """Check that *value* is a string that fits within this field.

        Parameters
        ----------
        value : str
            The string to validate.

        Returns
        -------
        bool
            Always ``True`` when valid.

        Raises
        ------
        TypeError
            If *value* is not a :class:`str`.
        ValueError
            If *value* encodes to more bytes than :attr:`length` under
            the configured *encoding*.
        """
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value).__name__!r}")
        try:
            encoded = value.encode(self.encoding)
        except UnicodeEncodeError as exc:
            raise ValueError(
                f"String {value!r} cannot be encoded as {self.encoding!r}: {exc}"
            ) from exc

        if len(encoded) > self.length:
            raise ValueError(
                f"String {value!r} encodes to {len(encoded)} bytes under "
                f"{self.encoding!r}, but field is only {self.length} byte(s) wide"
            )
        return True

    # ------------------------------------------------------------------
    # Encode / decode
    # ------------------------------------------------------------------

    def encode_bits(self, value: str, endian: str) -> str:  # noqa: ARG002
        """Encode *value* to a ``'0'``/``'1'`` string of length :attr:`bits`.

        Short strings are right-padded with :attr:`pad`; *endian* is ignored
        for string fields (bytes are always written left-to-right).

        Parameters
        ----------
        value : str
            Must already be validated.
        endian : {'big', 'little'}
            Accepted for interface consistency; has no effect.

        Returns
        -------
        str
            Bit string of length :attr:`bits`.
        """
        raw = value.encode(self.encoding)
        pad_b = self.pad.encode(self.encoding)

        # Pad to the full field width
        padded = raw + pad_b * (self.length - len(raw))

        return "".join(f"{byte:08b}" for byte in padded)

    def decode_bits(self, bit_str: str, endian: str) -> str:  # noqa: ARG002
        """Decode a bit string back to a string.

        Trailing pad characters are stripped from the decoded result.
        *endian* is ignored for string fields.

        Parameters
        ----------
        bit_str : str
            Exactly :attr:`bits` characters of ``'0'``/``'1'``.
        endian : {'big', 'little'}
            Accepted for interface consistency; has no effect.

        Returns
        -------
        str
            Decoded and pad-stripped string.
        """
        raw_bytes = bytes(int(bit_str[i : i + 8], 2) for i in range(0, len(bit_str), 8))

        decoded = raw_bytes.decode(self.encoding, errors="replace")

        # Strip trailing pad characters
        return decoded.rstrip(self.pad)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        """Short type description, e.g. ``ascii/8`` or ``utf-8/16``."""
        return f"{self.encoding}/{self.length}"

    def __repr__(self) -> str:
        """Detailed single-line representation.

        Example::

            StringType(ascii  8 bytes  pad=\\x00)
        """
        pad_repr = repr(self.pad) if self.pad == "\x00" else self.pad
        return f"StringType({self.encoding:<8} {self.length} bytes  pad={pad_repr})"


# ---------------------------------------------------------------------------
# Convenience factories
# ---------------------------------------------------------------------------


def str_type(length: int, pad: str = "\x00") -> StringType:
    """Create an ASCII :class:`StringType` of *length* bytes.

    This is the most common case — a null-terminated or null-padded ASCII
    string field.

    Parameters
    ----------
    length : int
        Field width in bytes.
    pad : str
        Pad character.  Default ``'\\x00'``.

    Examples
    --------
    >>> str_type(8)
    StringType(ascii    8 bytes  pad=\\x00)
    """
    return StringType(length=length, encoding="ascii", pad=pad)


def ascii_type(length: int, pad: str = "\x00") -> StringType:
    """Alias for :func:`str_type` — explicit ASCII :class:`StringType`.

    Examples
    --------
    >>> ascii_type(6)
    StringType(ascii    6 bytes  pad=\\x00)
    """
    return StringType(length=length, encoding="ascii", pad=pad)


def utf8_type(length: int, pad: str = "\x00") -> StringType:
    """Create a UTF-8 :class:`StringType` of *length* bytes.

    Note that *length* is the byte budget, not the character count —
    multibyte characters (e.g. emoji, CJK) consume more than one byte each.

    Parameters
    ----------
    length : int
        Field width in bytes.
    pad : str
        Pad character.  Default ``'\\x00'``.

    Examples
    --------
    >>> utf8_type(32)
    StringType(utf-8    32 bytes  pad=\\x00)
    """
    return StringType(length=length, encoding="utf-8", pad=pad)


def latin1_type(length: int, pad: str = "\x00") -> StringType:
    """Create a Latin-1 (ISO 8859-1) :class:`StringType` of *length* bytes.

    Latin-1 maps the first 256 Unicode code points directly to bytes, making
    it a lossless round-trip for any byte value — useful for legacy protocols
    that use extended ASCII.

    Parameters
    ----------
    length : int
        Field width in bytes.
    pad : str
        Pad character.  Default ``'\\x00'``.

    Examples
    --------
    >>> latin1_type(16)
    StringType(latin-1  16 bytes  pad=\\x00)
    """
    return StringType(length=length, encoding="latin-1", pad=pad)

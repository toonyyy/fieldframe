"""
fieldframe.fields.field
~~~~~~~~~~~~~~~~~~~~~~~

A single, named integer field inside a :class:`~fieldframe.core.Message`.

:class:`Field` is the most common building block in fieldframe.  It stores
one integer value (the *write* value, staged before encoding) and one decoded
result (the *read* value, populated after decoding).  The write setter
validates the value immediately, so bad data is caught at assignment time
rather than silently corrupted on the wire.

.. code-block:: python

    from fieldframe.fields.field import Field
    from fieldframe.types.int import uint_type, int_type

    altitude  = Field(name="altitude",  type=uint_type(16), default=0)
    heading   = Field(name="heading",   type=int_type(16),  default=0)

    altitude.write = 1500   # validated immediately
    altitude.write = 99999  # raises ValueError
"""

from fieldframe.types.int import IntType
from fieldframe.types.float import FloatType
from fieldframe.types.string import StringType
from fieldframe.frame.component import FrameComponent


class Field(FrameComponent):
    """A single fixed-width integer field within a message.

    Parameters
    ----------
    type : IntType
        Bit-width and signedness descriptor.
    name : str, optional
        Field name.  Set automatically when declared on a
        :class:`~fieldframe.core.Message` subclass.
    default : int, optional
        Initial write value.  Validated against *type* immediately.
        Defaults to ``0``.

    Attributes
    ----------
    read : int or None
        The last value decoded by :meth:`_decode_bits`.
        ``None`` until the field has been decoded at least once.
    write : int
        The value that will be encoded on the next :meth:`_encode_bits`
        call.  Assignment is validated immediately.

    Notes
    -----
    **Endianness** is a message-level concern passed in at encode/decode time:

    - Multi-byte fields (> 8 bits) are byte-swapped for little-endian messages.
    - Single-byte and sub-byte fields are never swapped.
    - Whole-frame bit-reversal is handled by :class:`~fieldframe.core.Message`,
      not here.

    Examples
    --------
    >>> from fieldframe.types.int import uint_type
    >>> f = Field(name="speed", type=uint_type(8), default=0)
    >>> f.write = 99
    >>> f._encode_bits("big")
    '01100011'
    """

    def __init__(
        self,
        type:    IntType|FloatType|StringType,
        name:    str = None,
        default: int = 0,
    ) -> None:
        self.name    = name
        self.type    = type
        self.default = default
        self.read:   int | None = None
        self._write: int | None = None  # backing store; set via property below
        self.write   = default          # runs validation immediately

    # ------------------------------------------------------------------
    # FrameComponent — required interface
    # ------------------------------------------------------------------

    def length(self) -> int:
        """Return the field width in bits."""
        return self.type.bits

    def _encode_bits(self, endian: str) -> str:
        """Encode :attr:`write` to a bit string.
 
        The value is always serialised MSB-first internally.  For
        little-endian messages with multi-byte fields the resulting bytes are
        then reversed so the least-significant byte appears first on the wire.
 
        Parameters
        ----------
        endian : {'big', 'little'}
            Byte order from the parent message.
 
        Returns
        -------
        str
            A ``'0'``/``'1'`` string of length :meth:`length`.
        """
        return self.type.encode_bits(self.write, endian)
 
    def _decode_bits(self, bit_str: str, endian: str) -> int:
        """Decode a bit string and store the result in :attr:`read`.
 
        For little-endian messages with multi-byte fields the byte order is
        reversed before interpretation so that ``ba2int`` always sees
        MSB-first data.
 
        Parameters
        ----------
        bit_str : str
            Exactly :meth:`length` characters of ``'0'``/``'1'``.
        endian : {'big', 'little'}
            Byte order from the parent message.
 
        Returns
        -------
        int
            The decoded integer (also stored in :attr:`read`).
        """
        self.read = self.type.decode_bits(bit_str, endian)
        return self.read

    # ------------------------------------------------------------------
    # write property — validates on every assignment
    # ------------------------------------------------------------------

    def _convert(self, value):
        if isinstance(self.type, IntType) and isinstance(value, str):
            try:
                value = int(value, 0)
            except ValueError:
                raise ValueError(
                    f"Field {self.name!r}: cannot convert string {value!r} to int"
                )
        return value

    @property
    def write(self) -> int:
        """Staged value to be encoded on the next encode call."""
        return self._write

    @write.setter
    def write(self, value: int) -> None:
        value = self._convert(value)
        self.type.validate(value)
        self._write = value

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _format(self, indent: int = 0) -> str:
        """Return an indented, box-drawn string for nested display."""
        pad   = "    " * indent
        bar   = "│"
        width = 28

        def row(label, value):
            return f"{pad}{bar}  {label:<10}{str(value):<{width}}{bar}"

        lines = [
            f"{pad}┌─ Field {'─' * (width + 4)}┐",
            row("name",    self.name  or "(unnamed)"),
            row("type",    self.type),
            row("default", self.default),
            row("write",   self.write),
            row("read",    self.read if self.read is not None else "—"),
            f"{pad}└{'─' * (width + 12)}┘",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        """Multi-line box representation showing all field state."""
        return self._format()

    def __repr__(self) -> str:
        """Compact single-line representation for quick inspection.

        Example::

            Field(speed, uint8, write=99, read=None)
        """
        read_str = "—" if self.read is None else str(self.read)
        return (
            f"Field({self.name or '?'}, {self.type}, "
            f"write={self.write}, read={read_str})"
        )
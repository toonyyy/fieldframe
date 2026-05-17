"""
fieldframe.fields.compute
~~~~~~~~~~~~~~~~~~~~~~~~~

A field whose value is **calculated at encode time** from the other fields
in the same message — typically used for lengths, checksums, or sequence
numbers that are derived from the payload.

.. code-block:: python

    from fieldframe.fields.compute import ComputedField
    from fieldframe.types.int import uint_type

    def xor_checksum(fields):
        acc = 0
        for f in fields:
            if hasattr(f, "write") and f.name != "checksum":
                acc ^= f.write
        return acc & 0xFF

    class Packet(Message):
        payload  = Field(type=uint_type(8), default=0)
        checksum = ComputedField(type=uint_type(8), compute=xor_checksum)

The ``compute`` callable receives the **full sibling field list** supplied by
:class:`~fieldframe.core.Message`, so it can inspect any other component to
derive the value it needs.

On **decode**, the compute function is *not* called — the on-wire value is
read directly into :attr:`read`, which lets you verify checksums / lengths
after receiving a frame.
"""

from fieldframe.types.int import IntType
from fieldframe.frame.component import FrameComponent


class ComputedField(FrameComponent):
    """A field whose value is derived from sibling fields at encode time.

    Parameters
    ----------
    type : IntType
        Bit-width and signedness descriptor for the computed value.
    compute : callable
        A function with signature ``(fields: list[FrameComponent]) -> int``.
        Receives the full sibling list; must return an integer that fits
        within *type*.
    name : str, optional
        Field name.  Set automatically when declared on a
        :class:`~fieldframe.core.Message` subclass.

    Attributes
    ----------
    read : int or None
        The last value decoded from the wire.  Populated by
        :meth:`_decode_bits`; ``None`` until first decode.

    Notes
    -----
    **Endianness** follows the same rules as :class:`~fieldframe.fields.field.Field`:
    multi-byte computed fields are byte-swapped for little-endian messages;
    single-byte and sub-byte fields are not.  Whole-frame bit-reversal is
    applied by :class:`~fieldframe.core.Message`, not here.
    """

    def __init__(
        self,
        name:    str     = None,
        type:    IntType = None,
        compute          = None,
        default: int     = 0,
    ) -> None:
        from fieldframe.types.int import uint_type as _uint8
        self.name    = name
        self.type    = type or _uint8(8)
        self.compute = compute
        self.default = default
        self._write: int        = default
        self.read:   int | None = None

    # ------------------------------------------------------------------
    # write property — reflects last computed value (or default)
    # ------------------------------------------------------------------

    @property
    def write(self) -> int:
        """Last computed value, or *default* before first encode."""
        return self._write

    # ------------------------------------------------------------------
    # FrameComponent — required interface
    # ------------------------------------------------------------------

    def length(self) -> int:
        """Return the field width in bits."""
        return self.type.bits

    def _encode_bits(self, endian: str, fields: list | None = None) -> str:
        """Invoke the compute function and encode the result.

        Parameters
        ----------
        endian : {'big', 'little'}
            Byte order from the parent message.
        fields : list[FrameComponent] or None
            Full sibling list passed in by :class:`~fieldframe.core.Message`.
            Defaults to ``[]`` as a safety net; in normal usage the message
            always supplies this.

        Returns
        -------
        str
            A ``'0'``/``'1'`` string of length :meth:`length`.

        Raises
        ------
        ValueError
            If the compute function returns a value outside the valid range
            for *type*.
        """
        value = self.compute(fields or [])
        self.type.validate(value)
        self._write = value                 # persist so next encode can reference it
        return self.type.encode_bits(value, endian)

    def _decode_bits(self, bit_str: str, endian: str) -> int:
        """Decode the on-wire value into :attr:`read`.

        The compute function is **not** called during decode — the raw
        wire value is stored directly so you can verify checksums / lengths
        on the receive path.

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
            f"{pad}┌─ ComputedField {'─' * (width + 6)}┐",
            row("name",    self.name or "(unnamed)"),
            row("type",    self.type),
            row("fn",      self.compute.__name__ if hasattr(self.compute, "__name__") else "λ"),
            row("default", self.default),
            row("write",   self._write),
            row("read",    self.read if self.read is not None else "—"),
            f"{pad}└{'─' * (width + 14)}┘",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        """Multi-line box representation showing field state."""
        return self._format()

    def __repr__(self) -> str:
        """Compact single-line representation for quick inspection.

        Example::

            ComputedField(checksum, uint8, fn=xor_checksum, read=None)
        """
        fn_name  = getattr(self.compute, "__name__", "λ")
        read_str = "—" if self.read is None else str(self.read)
        return (
            f"ComputedField({self.name or '?'}, {self.type}, "
            f"fn={fn_name}, read={read_str})"
        )
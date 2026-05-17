"""
fieldframe.fields.flags
~~~~~~~~~~~~~~~~~~~~~~~

A field that packs multiple named boolean flags into a single integer value
on the wire — a very common pattern in embedded and hardware protocols.

Instead of defining eight separate 1-bit fields for a status byte, declare
one :class:`FlagsField`:

.. code-block:: python

    from fieldframe.fields.flags import FlagsField
    from fieldframe.types.int import uint_type

    class StatusMessage(Message):
        flags = FlagsField(
            type=uint_type(8),
            flags=["armed", "locked", "error", "ready"],
        )

    msg = StatusMessage()
    msg.flags.armed = True
    msg.flags.ready = True

    bits = msg.encode()   # "10010000"

    recv = StatusMessage()
    recv.decode(bits)
    print(recv.flags.flag_reads)  # {"armed": True, "locked": False, ...}

Flags are addressed by attribute on the :class:`FlagsField` instance using
Python's descriptor / ``__getattr__`` / ``__setattr__`` machinery — see the
implementation notes in the source for details.

Bit ordering
------------
By default (``lsb_first=False``) the **first flag name maps to the MSB**.
This matches the way hardware protocol specifications are typically written
(*"bit 7 = armed"*).  Pass ``lsb_first=True`` for protocols that address bit 0
first (common in CAN / certain SPI configurations).
"""

from bitarray import bitarray
from bitarray.util import int2ba, ba2int

from fieldframe.types.int import IntType
from fieldframe.frame.component import FrameComponent


class _FlagProxy:
    """Thin boolean-like accessor returned by :meth:`FlagsField.__getattr__`.

    This object is what you hold when you write ``ff.armed``.  It behaves
    like a ``bool`` (via ``__bool__``) and supports assignment back to the
    parent field (via ``__set__``), so both of these work naturally::

        if msg.flags.armed: ...
        msg.flags.armed = True
    """

    __slots__ = ("_owner", "_name")

    def __init__(self, owner: "FlagsField", name: str) -> None:
        # Use object.__setattr__ to bypass FlagsField's own __setattr__
        object.__setattr__(self, "_owner", owner)
        object.__setattr__(self, "_name",  name)

    def __bool__(self) -> bool:
        """Evaluate the current write-side value of this flag."""
        return self._owner._flag_writes[self._name]

    def __repr__(self) -> str:
        value = self._owner._flag_writes[self._name]
        return f"FlagProxy({self._name}={value})"

    # Descriptor protocol — handles:  msg.flags.armed = True
    def __set__(self, obj, value: bool) -> None:
        self._owner._flag_writes[self._name] = bool(value)


class FlagsField(FrameComponent):
    """A fixed-width unsigned field whose bits are addressed by name.

    Parameters
    ----------
    type : IntType
        Must be **unsigned**.  Determines the total number of bits on the wire.
    flags : list[str]
        Flag names.  In MSB-first mode (default) the first name maps to the
        highest bit.  ``len(flags)`` must be ≤ ``type.bits``; any remaining
        low bits are reserved zeros.
    name : str, optional
        Set automatically when declared on a
        :class:`~fieldframe.core.Message` subclass.
    lsb_first : bool, optional
        When ``True``, ``flags[0]`` maps to bit 0 instead of the MSB.
        Default ``False``.

    Attributes
    ----------
    read : int or None
        Packed integer of the last decoded flag state.
        ``None`` until :meth:`_decode_bits` has been called at least once.
    write : int
        Read-only packed integer of the current write-side flag state.
    flag_writes : dict[str, bool]
        Copy of the write-side flag state as ``{name: bool}``.
    flag_reads : dict[str, bool]
        Copy of the last-decoded flag state as ``{name: bool}``.

    Raises
    ------
    TypeError
        If *type* is signed.
    ValueError
        If ``len(flags) > type.bits`` or flag names are not unique.

    Examples
    --------
    >>> ff = FlagsField(type=uint_type(8), flags=["armed", "locked"])
    >>> ff.armed = True
    >>> ff.write
    128
    >>> ff._encode_bits("big")
    '10000000'
    """

    def __init__(
        self,
        type:      IntType,
        flags:     list[str],
        name:      str = None,
        lsb_first: bool = False,
    ) -> None:
        if type.signed:
            raise TypeError(
                f"FlagsField requires an unsigned type, got {type}"
            )
        if len(flags) > type.bits:
            raise ValueError(
                f"Too many flags ({len(flags)}) for a {type.bits}-bit field"
            )
        if len(flags) != len(set(flags)):
            raise ValueError("Flag names must be unique")

        self.name      = name
        self.type      = type
        self.lsb_first = lsb_first
        self._names    = list(flags)

        # Write-side state — staged before encoding
        self._flag_writes: dict[str, bool] = {f: False for f in flags}
        # Read-side state — populated after decoding
        self._flag_reads:  dict[str, bool] = {f: False for f in flags}
        # Sentinel: True once _decode_bits has been called at least once
        self._decoded: bool = False

    # ------------------------------------------------------------------
    # FrameComponent — required interface
    # ------------------------------------------------------------------

    def length(self) -> int:
        """Return the field width in bits."""
        return self.type.bits

    def _encode_bits(self, endian: str) -> str:
        """Pack the write-side flags into a bit string.

        Parameters
        ----------
        endian : {'big', 'little'}
            Byte order from the parent message.  Multi-byte fields are
            byte-swapped for little-endian; single-byte fields are not.

        Returns
        -------
        str
            A ``'0'``/``'1'`` string of length :meth:`length`.
        """
        raw = int2ba(
            self._pack(self._flag_writes),
            length=self.type.bits,
            endian="big",
            signed=False,
        ).to01()

        if endian == "little" and self.type.bits > 8:
            chunks = [raw[i:i + 8] for i in range(0, len(raw), 8)]
            return "".join(reversed(chunks))

        return raw

    def _decode_bits(self, bit_str: str, endian: str) -> int:
        """Unpack a bit string into the read-side flag state.

        Parameters
        ----------
        bit_str : str
            Exactly :meth:`length` characters of ``'0'``/``'1'``.
        endian : {'big', 'little'}
            Byte order from the parent message.

        Returns
        -------
        int
            The packed integer value (also stored so :attr:`read` returns it).
        """
        if endian == "little" and len(bit_str) > 8:
            chunks = [bit_str[i:i + 8] for i in range(0, len(bit_str), 8)]
            bit_str = "".join(reversed(chunks))

        packed = ba2int(bitarray(bit_str), signed=False)
        self._flag_reads = self._unpack(packed)
        self._decoded    = True
        return packed

    # ------------------------------------------------------------------
    # Flag attribute access — ff.armed / ff.armed = True
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> _FlagProxy:
        """Return a :class:`_FlagProxy` for a known flag name.

        Only called by Python when normal attribute lookup has already failed,
        so real attributes (``name``, ``type``, etc.) are never intercepted.
        """
        writes = object.__getattribute__(self, "_flag_writes")
        if name in writes:
            return _FlagProxy(self, name)
        raise AttributeError(
            f"{self.__class__.__name__!r} has no flag {name!r}"
        )

    def __setattr__(self, name: str, value) -> None:
        """Route flag names to ``_flag_writes``; pass everything else through.

        Called for *every* attribute assignment, including those in
        ``__init__``.  Uses ``object.__getattribute__`` to safely check
        whether ``_flag_writes`` exists yet before trying to look inside it.
        """
        try:
            writes = object.__getattribute__(self, "_flag_writes")
        except AttributeError:
            # _flag_writes not yet created — still in __init__, set normally
            super().__setattr__(name, value)
            return

        if name in writes:
            writes[name] = bool(value)
        else:
            super().__setattr__(name, value)

    def __getitem__(self, name: str) -> bool:
        """Return a flag's current write-side value: ``ff['armed']``."""
        if name not in self._flag_writes:
            raise KeyError(f"No flag named {name!r}")
        return self._flag_writes[name]

    def __setitem__(self, name: str, value: bool) -> None:
        """Set a flag by name: ``ff['armed'] = True``."""
        if name not in self._flag_writes:
            raise KeyError(f"No flag named {name!r}")
        self._flag_writes[name] = bool(value)

    # ------------------------------------------------------------------
    # write / read properties (packed integer, consistent with Field)
    # ------------------------------------------------------------------

    @property
    def write(self) -> int:
        """Packed integer representation of the current write-side flag state."""
        return self._pack(self._flag_writes)

    @property
    def read(self) -> int | None:
        """Packed integer of the last decoded state, or ``None`` before first decode."""
        return None if not self._decoded else self._pack(self._flag_reads)

    @property
    def flag_writes(self) -> dict[str, bool]:
        """Write-side flag state as a ``{name: bool}`` copy."""
        return dict(self._flag_writes)

    @property
    def flag_reads(self) -> dict[str, bool]:
        """Last-decoded flag state as a ``{name: bool}`` copy."""
        return dict(self._flag_reads)

    # ------------------------------------------------------------------
    # Pack / unpack helpers
    # ------------------------------------------------------------------

    def _pack(self, flag_dict: dict[str, bool]) -> int:
        """Convert ``{name: bool}`` → packed integer."""
        packed = 0
        for i, name in enumerate(flag_dict):
            if flag_dict[name]:
                bit_pos = i if self.lsb_first else (self.type.bits - 1 - i)
                packed |= (1 << bit_pos)
        return packed

    def _unpack(self, packed: int) -> dict[str, bool]:
        """Convert packed integer → ``{name: bool}``."""
        result = {}
        for i, name in enumerate(self._names):
            bit_pos      = i if self.lsb_first else (self.type.bits - 1 - i)
            result[name] = bool(packed & (1 << bit_pos))
        return result

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _format(self, indent: int = 0) -> str:
        """Return an indented, box-drawn string for nested display."""
        pad   = "    " * indent
        bar   = "│"

        # Build the flags line  e.g.  [✓] armed   [✗] locked   [✗] error
        flag_parts = []
        for name, value in self._flag_writes.items():
            tick = "✓" if value else "✗"
            flag_parts.append(f"[{tick}] {name}")
        flags_str = "   ".join(flag_parts)

        # Determine box width from the widest row
        label_row = f"  {'name':<10}{self.name or '(unnamed)'}"
        type_row  = f"  {'type':<10}{self.type}  ({self.type.bits}-bit, lsb_first={self.lsb_first})"
        flags_row = f"  {'flags':<10}{flags_str}"
        read_val  = "—" if self.read is None else str(self.read)
        read_row  = f"  {'write':<10}{self.write}   read={read_val}"

        inner_width = max(len(r) for r in [label_row, type_row, flags_row, read_row]) + 2

        def boxed(content):
            return f"{pad}{bar}{content:<{inner_width}}{bar}"

        lines = [
            f"{pad}┌─ FlagsField {'─' * (inner_width - 13)}┐",
            boxed(label_row),
            boxed(type_row),
            boxed(flags_row),
            boxed(read_row),
            f"{pad}└{'─' * (inner_width)}┘",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        """Multi-line box representation showing all flag state."""
        return self._format()

    def __repr__(self) -> str:
        """Compact single-line representation for quick inspection.

        Example::

            FlagsField(status, uint8, armed=✓ locked=✗ error=✗ ready=✓)
        """
        flags_str = " ".join(
            f"{n}={'✓' if v else '✗'}"
            for n, v in self._flag_writes.items()
        )
        return (
            f"FlagsField({self.name or '?'}, {self.type}, {flags_str})"
        )
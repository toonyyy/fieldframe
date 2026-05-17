"""
fieldframe.core
~~~~~~~~~~~~~~~

The central :class:`Message` class — the container that ties fields,
computed fields, flag fields, and nested sub-messages together into a
structured binary frame.

A message can be built in two styles:

**Declarative subclass** (recommended for reusable message types)

.. code-block:: python

    from fieldframe.core import Message
    from fieldframe.fields.field import Field
    from fieldframe.types.int import uint_type, int_type

    class GuidanceMessage(Message):
        speed     = Field(type=uint_type(8), default=0)
        heading   = Field(type=int_type(16), default=0)

    msg = GuidanceMessage()
    msg.speed.write = 120
    bits = msg.encode()

**Direct instantiation** (useful for one-off or dynamic messages)

.. code-block:: python

    msg = Message("Guidance", [
        Field(name="speed",   type=uint_type(8),  default=0),
        Field(name="heading", type=int_type(16), default=0),
    ])

Nested sub-messages
-------------------
Any :class:`Message` instance can be used as a field inside another message.
Each sub-message manages its own ``endian`` and ``reversed`` settings
independently of its parent.

.. code-block:: python

    class Header(Message):
        version = Field(type=uint_type(4), default=1)
        msg_id  = Field(type=uint_type(12), default=0)

    class TelemetryPacket(Message):
        header   = Header()
        altitude = Field(type=uint_type(16), default=0)

Byte order and bit reversal
---------------------------
Pass ``endian="little"`` as a class keyword argument (or constructor
parameter) to byte-swap all multi-byte fields.  Pass ``reversed=True`` to
flip the entire assembled bitstream — useful for transports that transmit
LSB-first (some SPI modes, CAN signal definitions).
"""

import copy

from fieldframe.frame.component import FrameComponent
from fieldframe.fields.field import Field
from fieldframe.fields.compute import ComputedField


class Message(FrameComponent):
    """A structured binary message made up of :class:`FrameComponent` items.

    Parameters
    ----------
    name : str, optional
        Human-readable identifier.  Defaults to the class name.
    fields : list[FrameComponent], optional
        Explicit field list for direct instantiation.  Ignored when the class
        has fields declared as class variables (declarative style).
    endian : {'big', 'little'}, optional
        Byte order for all fields in this message.  Overrides the class-level
        default.  Default ``'big'``.
    reversed : bool, optional
        When ``True`` the assembled bitstream is reversed after encoding and
        before decoding.  Overrides the class-level default.  Default
        ``False``.

    Class keyword arguments
    -----------------------
    endian : {'big', 'little'}
        Default byte order for instances of this subclass.
    reversed : bool
        Default reversal setting.

    Examples
    --------
    >>> class Packet(Message):
    ...     speed = Field(type=uint_type(8), default=0)
    ...
    >>> p = Packet()
    >>> p.speed.write = 200
    >>> p.encode()
    '11001000'
    """

    # ------------------------------------------------------------------
    # Metaclass hook — runs once when a subclass body is evaluated
    # ------------------------------------------------------------------

    def __init_subclass__(
        cls,
        endian:   str  = "big",
        reversed: bool = False,
        **kwargs,
    ) -> None:
        super().__init_subclass__(**kwargs)

        cls._default_endian   = endian
        cls._default_reversed = reversed

        found = []
        for attr_name, val in cls.__dict__.items():
            if isinstance(val, FrameComponent):
                val.name = attr_name
                found.append((attr_name, val))

        if found:
            cls._fields_template = [val for _, val in found]
            for attr_name, _ in found:
                delattr(cls, attr_name)

    _fields_template:  list[FrameComponent] = []
    _default_endian:   str  = "big"
    _default_reversed: bool = False

    def __init__(
        self,
        name:     str                  = None,
        fields:   list[FrameComponent] = None,
        endian:   str                  = None,
        reversed: bool                 = None,
    ) -> None:
        cls = self.__class__

        self.endian   = endian   if endian   is not None else cls._default_endian
        self.reversal = reversed if reversed is not None else cls._default_reversed

        if self.endian not in ("big", "little"):
            raise ValueError(f"endian must be 'big' or 'little', got {self.endian!r}")

        self.name = name or cls.__name__

        if fields is not None:
            self.fields = list(fields)
        elif self._fields_template:
            self.fields = copy.deepcopy(self._fields_template)
        else:
            self.fields = []

        if fields is not None:
            unnamed = [f for f in self.fields if not f.name]
            if unnamed:
                raise ValueError(
                    f"All fields must have a name in direct style. "
                    f"Missing name on: {[type(f).__name__ for f in unnamed]}"
                )

    # ------------------------------------------------------------------
    # Length
    # ------------------------------------------------------------------

    def length(self) -> int:
        """Return the total message length in bits (sum of all components)."""
        return sum(c.length() for c in self.fields)

    # ------------------------------------------------------------------
    # FrameComponent implementation
    # ------------------------------------------------------------------

    def _encode_bits(self, endian: str = "big") -> str:
        """Encode using this message's own settings (sub-message entry point).

        The parent's *endian* argument is intentionally ignored; sub-messages
        are self-contained with respect to byte order.
        """
        bits = self._assemble_bits()
        return bits[::-1] if self.reversal else bits

    def _decode_bits(self, bit_str: str, endian: str = "big") -> dict:
        """Decode using this message's own settings (sub-message entry point).

        The parent's *endian* argument is intentionally ignored.
        """
        if self.reversal:
            bit_str = bit_str[::-1]
        self._disassemble_bits(bit_str)
        return self.read_values

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assemble_bits(self) -> str:
        """Encode every component using this message's endian. No reversal."""
        bits = []
        for component in self.fields:
            if isinstance(component, ComputedField):
                bits.append(component._encode_bits(self.endian, self.fields))
            else:
                bits.append(component._encode_bits(self.endian))
        return "".join(bits)

    def _disassemble_bits(self, bit_str: str) -> None:
        """Decode every component using this message's endian. No reversal."""
        pos = 0
        for component in self.fields:
            component._decode_bits(bit_str[pos:pos + component.length()], self.endian)
            pos += component.length()

    # ------------------------------------------------------------------
    # Public encode / decode API
    # ------------------------------------------------------------------

    def encode(self) -> str:
        """Encode all staged write values into a bit string.

        Returns
        -------
        str
            A ``'0'``/``'1'`` string of length :meth:`length`.
        """
        bits = self._assemble_bits()
        return bits[::-1] if self.reversal else bits

    def decode(self, bit_str: str) -> dict:
        """Decode a bit string into each component's read value.

        Parameters
        ----------
        bit_str : str
            A ``'0'``/``'1'`` string of exactly :meth:`length` characters.

        Returns
        -------
        dict
            ``{field_name: value}`` mapping.  Sub-messages appear as nested
            dicts.
        """
        if self.reversal:
            bit_str = bit_str[::-1]
        self._disassemble_bits(bit_str)
        return self.read_values

    def encode_bytes(self) -> bytes:
        """Encode to a byte array, padding to the next byte boundary."""
        from bitarray import bitarray as _bitarray
        return _bitarray(self._apply_padding(self.encode())).tobytes()

    def decode_bytes(self, data: bytes) -> dict:
        """Decode a byte array, stripping padding bits added by :meth:`encode_bytes`."""
        from bitarray import bitarray as _bitarray
        ba = _bitarray()
        ba.frombytes(data)
        return self.decode(self._strip_padding(ba.to01()))

    # ------------------------------------------------------------------
    # Alternative constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_bits(cls, bit_str: str) -> "Message":
        """Decode a bit string into a new instance (subclass only)."""
        if not cls._fields_template:
            raise TypeError(
                "from_bits() requires a Message subclass with declared fields."
            )
        instance = cls()
        instance.decode(bit_str)
        return instance

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        """Decode a byte array into a new instance (subclass only)."""
        if not cls._fields_template:
            raise TypeError(
                "from_bytes() requires a Message subclass with declared fields."
            )
        instance = cls()
        instance.decode_bytes(data)
        return instance

    # ------------------------------------------------------------------
    # Padding helpers
    # ------------------------------------------------------------------

    def _pad_count(self) -> int:
        remainder = self.length() % 8
        return 0 if remainder == 0 else 8 - remainder

    def _apply_padding(self, bit_str: str) -> str:
        pad = "0" * self._pad_count()
        return (bit_str + pad) if self.endian == "big" else (pad + bit_str)

    def _strip_padding(self, bit_str: str) -> str:
        pad = self._pad_count()
        if pad == 0:
            return bit_str
        return bit_str[:-pad] if self.endian == "big" else bit_str[pad:]

    # ------------------------------------------------------------------
    # Field staging and access
    # ------------------------------------------------------------------

    def set(self, **kwargs) -> None:
        """Stage write values by field name before encoding.

        Parameters
        ----------
        **kwargs
            ``field_name=value`` pairs.

        Raises
        ------
        KeyError
            If a name does not correspond to any field in this message.
        TypeError
            If the target component is a sub-message.
        ValueError
            If the value is out of range for the field's type.
        """
        field_map = {c.name: c for c in self.fields}
        for name, value in kwargs.items():
            if name not in field_map:
                raise KeyError(f"No field named {name!r} in {self.name!r}")
            component = field_map[name]
            if isinstance(component, Field):
                try:
                    component.write = value
                except (TypeError, ValueError) as exc:
                    raise type(exc)(f"Field {name!r}: {exc}") from exc
            else:
                raise TypeError(
                    f"{name!r} is a sub-message — use {name}.set(...) instead"
                )

    def __getattr__(self, name: str) -> FrameComponent:
        fields = object.__getattribute__(self, "fields")
        for component in fields:
            if component.name == name:
                return component
        raise AttributeError(
            f"{self.__class__.__name__!r} has no field or sub-message {name!r}"
        )

    def __getitem__(self, name: str) -> FrameComponent:
        """Return a field component by name: ``msg['speed']``."""
        field_map = {c.name: c for c in self.fields}
        if name not in field_map:
            raise KeyError(f"No field named {name!r} in {self.name!r}")
        return field_map[name]

    def __setitem__(self, name: str, value) -> None:
        field_map = {c.name: c for c in self.fields}
        if name not in field_map:
            raise KeyError(f"No field named {name!r} in {self.name!r}")
        component = field_map[name]
        if hasattr(component, "write"):
            component.write = value
        else:
            raise TypeError(
                f"{name!r} does not support direct assignment via [] — "
                f"use msg[{name!r}]['flag'] = True for FlagsField"
            )

    @property
    def write_values(self) -> dict:
        """All staged write values as ``{name: value}``. Sub-messages nested."""
        result = {}
        for component in self.fields:
            if isinstance(component, Message):
                result[component.name] = component.write_values
            else:
                result[component.name] = component.write
        return result

    @property
    def read_values(self) -> dict:
        """All last-decoded read values as ``{name: value}``. Sub-messages nested."""
        result = {}
        for component in self.fields:
            if isinstance(component, Message):
                result[component.name] = component.read_values
            else:
                result[component.name] = component.read
        return result

    # ------------------------------------------------------------------
    # Dynamic field manipulation
    # ------------------------------------------------------------------

    def add_field(self, component: FrameComponent, position: int = None) -> None:
        """Append or insert a component into this message."""
        if position is None:
            self.fields.append(component)
        else:
            if position > len(self.fields):
                raise IndexError(
                    f"Position {position} out of bounds "
                    f"({len(self.fields)} fields)"
                )
            self.fields.insert(position, component)

    def remove_field(self, position: int) -> None:
        """Remove the component at *position*."""
        if position >= len(self.fields):
            raise IndexError(
                f"Position {position} out of bounds "
                f"({len(self.fields)} fields)"
            )
        self.fields.pop(position)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _format(self, indent: int = 0) -> str:
        """Return a pretty-printed table for this message.

        Sub-messages are shown as a summary row in the parent table, then
        rendered in full below it — keeping the outer table clean and intact.

        Example output::

            ┌─ Message: TelemetryPacket  (big-endian, 48 bits) ────────┐
            │ name     │ type    │ write  │ read │
            ├──────────┼─────────┼────────┼──────┤
            │ header   │ Message │ 16 b   │      │
            │ altitude │ uint16  │ 0      │ —    │
            │ speed    │ uint8   │ 0      │ —    │
            │ footer   │ Message │ 8 b    │      │
            └──────────┴─────────┴────────┴──────┘

              ↳ header  (big-endian, 16 bits)
              ┌─────────┬────────┬───────┬──────┐
              │ version │ uint4  │ 1     │ —    │
              │ msg_id  │ uint12 │ 0     │ —    │
              └─────────┴────────┴───────┴──────┘
        """
        from fieldframe.fields.flags import FlagsField

        pad = "\t" * indent

        # ----------------------------------------------------------
        # Determine column widths by scanning all leaf components
        # ----------------------------------------------------------
        col_name  = len("name")
        col_type  = len("type")
        col_write = len("write")
        col_read  = len("read")

        for c in self.fields:
            col_name  = max(col_name,  len(str(c.name or "")))
            col_type  = max(col_type,  len("Message" if isinstance(c, Message)
                                           else str(getattr(c, "type", ""))))
            if not isinstance(c, Message):
                write_v = c.write if hasattr(c, "write") else ""
                read_v  = c.read  if hasattr(c, "read")  else ""
                if isinstance(c, FlagsField):
                    # show flag state instead of the packed int
                    write_s = "  ".join(
                        f"{'✓' if v else '✗'}{n}"
                        for n, v in c.flag_writes.items()
                    )
                else:
                    write_s = "" if write_v is None else str(write_v)
                read_s  = "" if read_v  is None else str(read_v)
                col_write = max(col_write, len(write_s))
                col_read  = max(col_read,  len(read_s))

        # ensure sub-message summary fits in write column
        col_write = max(col_write, len("(sub-message)"))

        # ----------------------------------------------------------
        # Helper: one table row
        # ----------------------------------------------------------
        def row(name_s, type_s, write_s, read_s):
            return (
                f"{pad}│ {name_s:<{col_name}} "
                f"│ {type_s:<{col_type}} "
                f"│ {write_s:<{col_write}} "
                f"│ {read_s:<{col_read}} │"
            )

        sep = (
            f"{pad}├{'─'*(col_name+2)}┼{'─'*(col_type+2)}"
            f"┼{'─'*(col_write+2)}┼{'─'*(col_read+2)}┤"
        )
        _ = (
            f"{pad}┌{'─'*(col_name+2)}┬{'─'*(col_type+2)}"
            f"┬{'─'*(col_write+2)}┬{'─'*(col_read+2)}┐"
        )
        bot = (
            f"{pad}└{'─'*(col_name+2)}┴{'─'*(col_type+2)}"
            f"┴{'─'*(col_write+2)}┴{'─'*(col_read+2)}┘"
        )

        # ----------------------------------------------------------
        # Title line (above the column-header row)
        # ----------------------------------------------------------
        rev_tag   = ", reversed" if self.reversal else ""
        title     = f" {self.name}  ({self.endian}-endian{rev_tag}, {self.length()} bits)"
        title_width = col_name + col_type + col_write + col_read + 13
        title_bar = (
            f"{pad}┌─ Message: "
            f"{title}{'─' * max(0, title_width - len(title) - 11)}┐"
        )

        # ----------------------------------------------------------
        # Assemble main table
        # ----------------------------------------------------------
        lines = [
            title_bar,
            row("name", "type", "write", "read"),
            sep,
        ]

        sub_messages = []   # collect for rendering below the table

        for c in self.fields:
            if isinstance(c, Message):
                lines.append(row(
                    str(c.name or ""),
                    "Message",
                    f"{c.length()} bits",
                    "",
                ))
                sub_messages.append(c)
            else:
                if isinstance(c, FlagsField):
                    write_s = "  ".join(
                        f"{'✓' if v else '✗'}{n}"
                        for n, v in c.flag_writes.items()
                    )
                else:
                    write_v = c.write if hasattr(c, "write") else None
                    write_s = "" if write_v is None else str(write_v)

                read_v = c.read if hasattr(c, "read") else None
                read_s = "—" if read_v is None else str(read_v)

                lines.append(row(
                    str(c.name or ""),
                    str(getattr(c, "type", "")),
                    write_s,
                    read_s,
                ))

        lines.append(bot)

        # ----------------------------------------------------------
        # Render sub-messages below the parent table
        # ----------------------------------------------------------
        for sub in sub_messages:
            lines.append("")
            lines.append(f"{pad}\t↳ {sub.name}  ({sub.endian}-endian, {sub.length()} bits)")
            lines.append(sub._format(indent + 1))

        return "\n".join(lines)

    def __str__(self) -> str:
        """Pretty-printed table showing all fields and their current state."""
        return self._format()

    def __repr__(self) -> str:
        """Compact single-line summary for quick inspection.

        Example::

            Message(GuidanceMessage, big-endian, 24 bits, 3 fields)
        """
        return (
            f"Message({self.name}, {self.endian}-endian, "
            f"{self.length()} bits, {len(self.fields)} fields)"
        )
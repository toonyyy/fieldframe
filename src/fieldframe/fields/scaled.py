"""
fieldframe.fields.scaled
~~~~~~~~~~~~~~~~~~~~~~~~

A field that stores a floating-point logical value as a compact unsigned
integer on the wire — a very common pattern in embedded and CAN bus protocols
where you need float-like range but want to minimise frame size.

Given a ``min_val``, ``max_val``, and ``resolution``, the field:

- **Calculates its own bit width** automatically from the number of discrete
  steps needed to cover the range at the given resolution.
- **Encodes** by converting the float to an integer index:
  ``wire_int = round((value - min_val) / resolution)``
- **Decodes** by reversing that:
  ``value = min_val + wire_int * resolution``

.. code-block:: python

    from fieldframe.fields.scaled import ScaledField

    class SensorFrame(Message):
        # -40 °C to +85 °C in 0.1 °C steps → 11 bits on the wire
        temperature = ScaledField(
            name="temperature",
            min_val=-40.0, max_val=85.0, resolution=0.1,
        )

        # 0 % to 100 % in 0.5 % steps → 8 bits on the wire
        throttle = ScaledField(
            name="throttle",
            min_val=0.0, max_val=100.0, resolution=0.5,
        )

On **encode** the float write-value is quantised to the nearest resolution
step and packed as a ``uint`` of the calculated width.

On **decode** the wire integer is converted back to a float.  The ``read``
attribute always holds a float; the raw wire integer is available via
:attr:`read_raw`.

Bit width calculation
---------------------
::

    steps     = round((max_val - min_val) / resolution)
    bits      = ceil(log2(steps + 1))

For example, temperature above:
    steps = round((85 − (−40)) / 0.1) = 1250
    bits  = ceil(log2(1251))          = 11
"""

import math
from fieldframe.types.int import uint_type
from fieldframe.frame.component import FrameComponent


class ScaledField(FrameComponent):
    """A fixed-width field whose logical value is a float in ``[min_val, max_val]``.

    The wire representation is a compact unsigned integer; all float ↔ int
    conversion happens transparently at encode/decode time.

    Parameters
    ----------
    name : str
        Field name.
    min_val : float
        Minimum logical value (inclusive).  Maps to wire integer ``0``.
    max_val : float
        Maximum logical value (inclusive).  Maps to wire integer ``steps``.
    resolution : float
        Smallest representable step.  Must be > 0 and small enough that at
        least one step exists between ``min_val`` and ``max_val``.
    default : float, optional
        Initial write value.  Defaults to ``min_val``.

    Attributes
    ----------
    steps : int
        Total number of discrete steps: ``round((max_val - min_val) / resolution)``.
    bits : int
        Wire width in bits: ``ceil(log2(steps + 1))``.
    read : float or None
        Last decoded logical value.  ``None`` until first decode.
    read_raw : int or None
        Raw wire integer from the last decode.  ``None`` until first decode.

    Raises
    ------
    ValueError
        If ``min_val >= max_val``, ``resolution <= 0``, or the default value
        is outside ``[min_val, max_val]``.

    Examples
    --------
    >>> sf = ScaledField(name="temp", min_val=-40.0, max_val=85.0, resolution=0.1)
    >>> sf.bits
    11
    >>> sf.write = 25.0
    >>> sf._encode_bits("big")   # 650 encoded as 11-bit uint
    '01010001010'
    """

    def __init__(
        self,
        min_val:    float,
        max_val:    float,
        resolution: float,
        name:       str = None,
        default:    float = None,
    ) -> None:
        if min_val >= max_val:
            raise ValueError(
                f"min_val ({min_val}) must be less than max_val ({max_val})"
            )
        if resolution <= 0:
            raise ValueError(
                f"resolution must be > 0, got {resolution}"
            )

        steps = round((max_val - min_val) / resolution)
        if steps < 1:
            raise ValueError(
                f"Resolution {resolution} is too coarse for range "
                f"[{min_val}, {max_val}] — produces 0 steps"
            )

        bits = max(1, math.ceil(math.log2(steps + 1)))

        self.name       = name
        self.min_val    = float(min_val)
        self.max_val    = float(max_val)
        self.resolution = float(resolution)
        self.steps      = steps
        self._int_type  = uint_type(bits)

        # Derive decimal places from resolution for clean round-trip display
        self._dp = self._decimal_places()

        self.read:     float | None = None
        self.read_raw: int   | None = None

        # Set write via property so validation runs
        self._write: float = self.min_val
        self.write = float(default) if default is not None else self.min_val

    # ------------------------------------------------------------------
    # FrameComponent — required interface
    # ------------------------------------------------------------------

    @property
    def bits(self) -> int:
        """Wire width in bits — shorthand for :meth:."""
        return self._int_type.bits

    @property
    def type(self):
        class _Display:
            def __init__(self, bits):
                self.bits = bits
            def __str__(self):
                return f"scaled/{self.bits}b"
        return _Display(self._int_type.bits)

    def length(self) -> int:
        """Return the wire width in bits."""
        return self._int_type.bits

    def _encode_bits(self, endian: str) -> str:
        """Quantise the write value and encode as an unsigned integer.

        Parameters
        ----------
        endian : {'big', 'little'}
            Byte order from the parent message.

        Returns
        -------
        str
            A ``'0'``/``'1'`` string of length :meth:`length`.
        """
        wire_int = self._to_int(self._write)
        return self._int_type.encode_bits(wire_int, endian)

    def _decode_bits(self, bit_str: str, endian: str) -> float:
        """Decode the wire integer and convert back to a float.

        Parameters
        ----------
        bit_str : str
            Exactly :meth:`length` characters of ``'0'``/``'1'``.
        endian : {'big', 'little'}
            Byte order from the parent message.

        Returns
        -------
        float
            The decoded logical value (also stored in :attr:`read`).
        """
        self.read_raw = self._int_type.decode_bits(bit_str, endian)
        self.read     = self._to_float(self.read_raw)
        return self.read

    # ------------------------------------------------------------------
    # write property
    # ------------------------------------------------------------------

    @property
    def write(self) -> float:
        """Logical float value staged for the next encode."""
        return self._write

    @write.setter
    def write(self, value) -> None:
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                raise ValueError(
                    f"ScaledField {self.name!r}: cannot convert {value!r} to float"
                )
        self._validate(value)
        self._write = float(value)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"ScaledField {self.name!r}: expected float or int, "
                f"got {type(value).__name__!r}"
            )
        if not (self.min_val <= value <= self.max_val):
            raise ValueError(
                f"ScaledField {self.name!r}: {value} is out of range "
                f"[{self.min_val}, {self.max_val}]"
            )

    def _to_int(self, value: float) -> int:
        """Convert logical float → wire unsigned integer, clamped to valid range."""
        raw = (value - self.min_val) / self.resolution
        return min(self.steps, max(0, round(raw)))

    def _to_float(self, int_val: int) -> float:
        """Convert wire unsigned integer → logical float, rounded to resolution."""
        return round(self.min_val + int_val * self.resolution, self._dp)

    def _decimal_places(self) -> int:
        """Infer decimal places from resolution to keep decoded values clean."""
        s = f"{self.resolution:.10f}".rstrip("0")
        return len(s.split(".")[1]) if "." in s else 0

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _format(self, indent: int = 0) -> str:
        pad   = "    " * indent
        bar   = "│"
        width = 28

        def row(label, value):
            return f"{pad}{bar}  {label:<12}{str(value):<{width}}{bar}"

        read_str     = "—" if self.read     is None else str(self.read)
        read_raw_str = "—" if self.read_raw is None else str(self.read_raw)
        wire_int     = self._to_int(self._write)

        lines = [
            f"{pad}┌─ ScaledField {'─' * (width + 6)}┐",
            row("name",       self.name or "(unnamed)"),
            row("range",      f"[{self.min_val}, {self.max_val}]"),
            row("resolution", self.resolution),
            row("steps",      f"{self.steps}  ({self._int_type.bits}-bit wire)"),
            row("write",      f"{self._write}  (wire={wire_int})"),
            row("read",       f"{read_str}  (wire={read_raw_str})"),
            f"{pad}└{'─' * (width + 16)}┘",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self._format()

    def __repr__(self) -> str:
        """Compact single-line representation.

        Example::

            ScaledField(temp, [-40.0, 85.0], res=0.1, 11-bit, write=25.0)
        """
        return (
            f"ScaledField({self.name or '?'}, "
            f"[{self.min_val}, {self.max_val}], "
            f"res={self.resolution}, "
            f"{self._int_type.bits}-bit, "
            f"write={self._write})"
        )
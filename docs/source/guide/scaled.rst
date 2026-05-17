Scaled Field
============

:class:`~fieldframe.fields.scaled.ScaledField` stores a floating-point
logical value as a compact unsigned integer on the wire. This is a very
common pattern in CAN bus and embedded protocols where you need float-like
range but want to minimise frame size.

You define the physical range and resolution — fieldframe calculates the
required bit width automatically:

.. code-block:: python

   from fieldframe import Message, ScaledField

   class SensorFrame(Message):
       # -40 °C to +85 °C in 0.1 °C steps → 11 bits on the wire
       temperature = ScaledField(
           name="temperature",
           min_val=-40.0,
           max_val=85.0,
           resolution=0.1,
       )

Bit width calculation
---------------------

The wire width is derived from the number of discrete steps needed to cover
the range at the given resolution:

.. code-block:: text

   steps = round((max_val - min_val) / resolution)
   bits  = ceil(log2(steps + 1))

For the temperature example above:

.. code-block:: text

   steps = round((85 − (−40)) / 0.1) = 1250
   bits  = ceil(log2(1251))          = 11

No manual bit-width sizing is needed.

Encoding and decoding
---------------------

On **encode**, the float write-value is quantised to the nearest resolution
step and packed as an unsigned integer:

.. code-block:: text

   wire_int = round((value - min_val) / resolution)

On **decode**, the wire integer is converted back to a float:

.. code-block:: text

   value = min_val + wire_int * resolution

.. code-block:: python

   msg = SensorFrame()
   msg.temperature.write = 25.0

   bits = msg.encode()

   recv = SensorFrame.from_bits(bits)
   print(recv.temperature.read)      # 25.0
   print(recv.temperature.read_raw)  # 650  (the raw wire integer)

Accessing values
----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Attribute
     - Description
   * - ``sf.write``
     - Logical float staged for the next encode
   * - ``sf.read``
     - Logical float from the last decode (``None`` until first decode)
   * - ``sf.read_raw``
     - Raw wire integer from the last decode (``None`` until first decode)
   * - ``sf.steps``
     - Total number of discrete steps
   * - ``sf.bits``
     - Wire width in bits

Validation
----------

Assigning a value outside ``[min_val, max_val]`` raises :exc:`ValueError`
immediately:

.. code-block:: python

   msg.temperature.write = 100.0   # raises ValueError — above max_val

Pretty printing
---------------

.. code-block:: python

   print(msg.temperature)

.. code-block:: text

   ┌─ ScaledField ──────────────────────────────┐
   │  name        temperature                   │
   │  range       [-40.0, 85.0]                 │
   │  resolution  0.1                           │
   │  steps       1250  (11-bit wire)           │
   │  write       25.0  (wire=650)              │
   │  read        —     (wire=—)                │
   └────────────────────────────────────────────┘
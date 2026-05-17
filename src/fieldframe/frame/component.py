"""
fieldframe.frame.component
~~~~~~~~~~~~~~~~~~~~~~~~~~

Abstract base class for every element that can participate in a
:class:`~fieldframe.core.Message` encode / decode cycle.

All concrete types — :class:`~fieldframe.fields.field.Field`,
:class:`~fieldframe.fields.compute.ComputedField`,
:class:`~fieldframe.fields.flags.FlagsField`, and
:class:`~fieldframe.core.Message` itself — inherit from
:class:`FrameComponent` and must implement its three abstract methods.

Typical usage
-------------
You will not instantiate ``FrameComponent`` directly.  It exists purely as a
contract:

.. code-block:: python

    from fieldframe.frame.component import FrameComponent

    class MyField(FrameComponent):
        def length(self) -> int: ...
        def _encode_bits(self, endian: str) -> str: ...
        def _decode_bits(self, bit_str: str, endian: str) -> object: ...
        def _format(self, indent: int = 0) -> str: ...
"""

from abc import ABC, abstractmethod


class FrameComponent(ABC):
    """Abstract base for every encodable / decodable element in a message.

    A ``FrameComponent`` occupies a contiguous slice of bits inside a
    :class:`~fieldframe.core.Message`.  The ``Message`` encode / decode loop
    works exclusively in terms of this interface, so any custom component
    that satisfies it slots in without any changes to the core.

    Attributes
    ----------
    name : str or None
        Assigned automatically by :meth:`Message.__init_subclass__` when the
        component is declared as a class variable on a ``Message`` subclass.
        Can also be passed explicitly to the component's constructor.

    Notes
    -----
    **Endianness is a Message-level concern.**
    The ``Message`` resolves its ``endian`` setting once and passes it into
    every ``_encode_bits`` / ``_decode_bits`` call.  Leaf fields
    (:class:`~fieldframe.fields.field.Field`,
    :class:`~fieldframe.fields.compute.ComputedField`,
    :class:`~fieldframe.fields.flags.FlagsField`) consume that value to
    decide whether to byte-swap multi-byte values.  Sub-messages ignore it
    entirely and substitute their own stored ``endian``.
    """

    @abstractmethod
    def length(self) -> int:
        """Return the size of this component in bits.

        Returns
        -------
        int
            A positive integer.  Must be consistent across calls for a given
            instance so that the ``Message`` can correctly slice the bitstream.
        """
        ...

    @abstractmethod
    def _encode_bits(self, endian: str) -> str:
        """Encode this component to a bit string.

        Parameters
        ----------
        endian : {'big', 'little'}
            The parent message's byte-order setting.  Leaf fields use this to
            decide whether to byte-swap multi-byte values.  Sub-messages
            substitute their own stored ``endian`` and ignore this argument.

        Returns
        -------
        str
            A string of ``'0'`` / ``'1'`` characters whose length equals
            :meth:`length`.
        """
        ...

    @abstractmethod
    def _decode_bits(self, bit_str: str, endian: str) -> object:
        """Decode a bit string into this component.

        Parameters
        ----------
        bit_str : str
            Exactly :meth:`length` characters of ``'0'`` / ``'1'``.
        endian : {'big', 'little'}
            The parent message's byte-order setting.

        Returns
        -------
        object
            The decoded value.  The component must also store the result
            internally so it can be retrieved later (via ``.read`` on leaf
            fields, or ``.read_values`` on messages).
        """
        ...

    @abstractmethod
    def _format(self, indent: int = 0) -> str:
        """Return a human-readable, indented representation.

        Parameters
        ----------
        indent : int
            Number of tab characters to prepend.  Used by
            :class:`~fieldframe.core.Message` when recursively formatting
            nested sub-messages.

        Returns
        -------
        str
        """
        ...
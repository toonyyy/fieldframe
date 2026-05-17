"""
fieldframe.protocols
~~~~~~~~~~~~~~~~~~~~

High-level protocol container that groups a shared :class:`~fieldframe.core.Message`
header, an optional footer, and a registry of message types — each identified
by a key field in the header.

A :class:`Protocol` lets you decode an arbitrary incoming bitstream without
knowing its type in advance: the header is decoded first, the key field is
read, and the matching message is selected automatically.

**Declarative subclass** (recommended for fixed, reusable protocols):

.. code-block:: python

    from fieldframe.protocols import Protocol
    from fieldframe.core import Message
    from fieldframe.fields.field import Field
    from fieldframe.types.int import uint_type

    class MyProtocol(Protocol, key="msg_id", name="MyProtocol"):

        class Header(Message):
            msg_id  = Field(type=uint_type(8), default=0)
            version = Field(type=uint_type(8), default=1)

        class TelemetryMessage(Message):
            _msg_id  = 1
            altitude = Field(type=uint_type(16), default=0)

        class CommandMessage(Message):
            _msg_id  = 2
            command  = Field(type=uint_type(8), default=0)

    proto = MyProtocol()
    result = proto.decode(incoming_bits)

**Direct instantiation** (useful for dynamic or one-off protocols):

.. code-block:: python

    proto = Protocol(
        name="MyProtocol",
        header=Header(),
        key="msg_id",
        messages={"1": TelemetryMessage(), "2": CommandMessage()},
    )

Key field
---------
The ``key`` is the name of a field in the header whose value identifies which
message type the bitstream contains.  Each message in the registry is stored
under the string representation of its key value — e.g. ``"1"`` for
``_msg_id = 1``.

Header / footer injection
-------------------------
When a header or footer is set, a deep copy is automatically prepended or
appended to every registered message.  This ensures each message instance
carries its own independent header/footer state and can be encoded or decoded
in isolation.
"""

import copy
from fieldframe.core import Message


class Protocol:
    """A registry of typed messages sharing a common header (and optional footer).

    The protocol decodes an incoming bitstream by first reading the header,
    extracting the key field value, and dispatching to the matching registered
    message for full decoding.

    Args:
        name (str, optional): Human-readable protocol name. Defaults to the
            class name.
        messages (dict[str, Message], optional): Registry mapping key value
            strings to :class:`~fieldframe.core.Message` instances. Defaults
            to an empty dict.
        header (Message): The shared header message prepended to every
            registered message. Required.
        key (str): Name of the field in *header* whose value identifies the
            message type. Required.
        footer (Message, optional): Shared footer message appended to every
            registered message. Defaults to ``None``.

    Raises:
        TypeError: If *header* is not a :class:`~fieldframe.core.Message`, or
            if *footer* is set and is not a ``Message``.
        ValueError: If *key* is not the name of a field in *header*.
        AttributeError: If *header* or *footer* are reassigned after
            initialisation.

    Examples:
        >>> proto = MyProtocol()
        >>> result = proto.decode(incoming_bits)
        >>> proto.display()
    """

    # ------------------------------------------------------------------
    # Declarative subclass support
    # ------------------------------------------------------------------

    _proto_key: str | None = None
    _proto_name: str | None = None
    _proto_header_cls: type | None = None
    _proto_footer_cls: type | None = None
    _proto_message_clss: dict = {}

    def __init_subclass__(
        cls,
        key: str = None,
        name: str = None,
        **kwargs,
    ) -> None:
        """Collect header, footer, and message classes from the subclass body.

        Called automatically by Python when a subclass of :class:`Protocol` is
        defined. Scans the subclass namespace for:

        - A nested class named ``Header`` — used as the shared header.
        - A nested class named ``Footer`` — used as the optional shared footer.
        - Any other nested :class:`~fieldframe.core.Message` subclass that has
          a ``_msg_id`` attribute — registered as a typed message.

        Args:
            key (str, optional): Name of the header field used to identify
                message types. Passed as a class keyword argument.
            name (str, optional): Human-readable protocol name. Passed as a
                class keyword argument.
            **kwargs: Forwarded to :func:`super().__init_subclass__`.
        """
        super().__init_subclass__(**kwargs)

        cls._proto_key = key
        cls._proto_name = name

        cls._proto_header_cls = None
        cls._proto_footer_cls = None
        cls._proto_message_clss = {}

        for attr_name, val in cls.__dict__.items():
            if not isinstance(val, type) or not issubclass(val, Message):
                continue
            if attr_name == "Header":
                cls._proto_header_cls = val
            elif attr_name == "Footer":
                cls._proto_footer_cls = val
            elif hasattr(val, "_msg_id") and val._msg_id is not None:
                cls._proto_message_clss[str(val._msg_id)] = val

    # ------------------------------------------------------------------
    # Constructor — supports both direct and declarative styles
    # ------------------------------------------------------------------

    def __init__(
        self,
        name: str = None,
        messages: dict[str, Message] = None,
        header: Message = None,
        key: str = None,
        footer: Message | None = None,
    ) -> None:
        cls = self.__class__

        if header is None and cls._proto_header_cls is not None:
            header = cls._proto_header_cls()
        if messages is None and cls._proto_message_clss:
            messages = {k: v() for k, v in cls._proto_message_clss.items()}
        if key is None and cls._proto_key is not None:
            key = cls._proto_key
        if name is None:
            name = cls._proto_name or cls.__name__
        if footer is None and cls._proto_footer_cls is not None:
            footer = cls._proto_footer_cls()

        self._initialised = False

        self.name = name
        self.messages = messages or {}

        self.header = header
        self.footer = footer
        self.key = key

        self._add_keys()

        self._initialised = True

    # ------------------------------------------------------------------
    # Checks for header, footer and key
    # ------------------------------------------------------------------

    @property
    def header(self) -> Message:
        """The shared header message.

        A deep copy of this message is prepended to every registered message
        at construction time. Cannot be changed after initialisation.

        Raises:
            AttributeError: If set after the protocol is initialised.
            TypeError: If the value is not a :class:`~fieldframe.core.Message`.
        """
        return self._header

    @header.setter
    def header(self, value: Message) -> None:
        if self._initialised:
            raise AttributeError("header cannot be changed after initialisation")
        if not isinstance(value, Message):
            raise TypeError("header must be a Message")
        self._header = value
        for _, msg in self.messages.items():
            msg.add_field(component=copy.deepcopy(value), position=0)

    @property
    def footer(self) -> Message | None:
        """The shared footer message, or ``None`` if no footer is defined.

        A deep copy of this message is appended to every registered message
        at construction time. Cannot be changed after initialisation.

        Raises:
            AttributeError: If set after the protocol is initialised.
            TypeError: If the value is not a :class:`~fieldframe.core.Message`
                or ``None``.
        """
        return self._footer

    @footer.setter
    def footer(self, value: Message | None) -> None:
        if self._initialised:
            raise AttributeError("footer cannot be changed after initialisation")
        if value is not None and not isinstance(value, Message):
            raise TypeError("footer must be a Message or None")
        self._footer = value
        if value is not None:
            for _, msg in self.messages.items():
                msg.add_field(component=copy.deepcopy(value))

    @property
    def key(self) -> str:
        """Name of the header field used to identify message types.

        Must match a field name in :attr:`header`. Used during
        :meth:`decode` to look up the correct message from the registry.

        Raises:
            ValueError: If the value is not the name of a field in
                :attr:`header`.
        """
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        if value not in [field.name for field in self.header.fields]:
            raise ValueError("Not a valid key as it not a field in the header message")
        self._key = value

    # ------------------------------------------------------------------
    # Auto add key value to each header
    # ------------------------------------------------------------------

    def _add_keys(self) -> None:
        """Stamp the key field value into the header of every registered message.

        Called once at the end of ``__init__``. Iterates over
        :attr:`messages` and writes each message's registry key into its
        embedded header field so that encoded frames carry the correct
        identifier automatically.
        """
        for key_id, msg in self.messages.items():
            self._add_key_value(msg=msg, key_value=key_id)

    def _add_key_value(self, msg: Message, key_value: str) -> None:
        """Write *key_value* into the key field of *msg*'s embedded header.

        Args:
            msg (Message): The registered message to update.
            key_value (str): The string key value to write into the header's
                key field.
        """
        msg[self.header.name][self.key] = key_value

    # ------------------------------------------------------------------
    # Add / remove messages in a protocol
    # ------------------------------------------------------------------

    def add_message(self, name: str, message: Message) -> None:
        """Register a new message type under *name*.

        Args:
            name (str): The key value string to register the message under.
                Must not already exist in the registry.
            message (Message): The message instance to register.

        Raises:
            ValueError: If a message with *name* is already registered.

        Examples:
            >>> proto.add_message("3", CommandMessage())
        """
        if name in self.messages:
            raise ValueError(f"Message of name {name} already in protocol")

        self.messages[name] = message

    def remove_message(self, name: str) -> None:
        """Remove a registered message type by key name.

        Args:
            name (str): The key value string of the message to remove.

        Raises:
            ValueError: If no message with *name* is registered.

        Examples:
            >>> proto.remove_message("3")
        """
        if name not in self.messages:
            raise ValueError(f"Message of name {name} not in protocol")

        del self.messages[name]

    # ------------------------------------------------------------------
    # Access messages in protocol
    # ------------------------------------------------------------------

    def get_message(self, name: str) -> Message:
        """Return a registered message by its message name (not key value).

        Searches all registered messages by their ``name`` attribute rather
        than their registry key, so you can look up by the human-readable
        class name rather than the numeric key string.

        Args:
            name (str): The ``name`` attribute of the message to retrieve.

        Returns:
            Message: The matching registered message instance.

        Raises:
            ValueError: If no registered message has a matching name.

        Examples:
            >>> msg = proto.get_message("TelemetryMessage")
        """
        for _, msg in self.messages.items():
            if name == msg.name:
                return msg
        raise ValueError(f"Message of name {name} not defined in protocol {self.name}")

    # ------------------------------------------------------------------
    # Decode a given message
    # ------------------------------------------------------------------

    def decode(self, bit_str: str) -> dict:
        """Decode a bitstream by dispatching to the correct registered message.

        Decodes the header first to extract the key field value, then looks up
        the matching message and performs a full decode of the entire
        bitstream.

        Args:
            bit_str (str): A ``'0'``/``'1'`` string containing a complete
                framed message — header, payload, and optional footer.

        Returns:
            dict: The decoded field values from the matched message, in the
                same format as :meth:`~fieldframe.core.Message.decode`.

        Raises:
            KeyError: If the key field value cannot be found in the decoded
                header, or if no registered message matches that key value.

        Examples:
            >>> result = proto.decode("0000000100101100")
            >>> result["altitude"]
            300
        """
        res = self.header.decode(bit_str[0 : self.header.length()])
        key_value = res.get(self.key, None)

        if key_value is None:
            raise KeyError(f"Key value of {self.key} could not be found in message")

        msg = self.messages.get(str(key_value), None)

        if msg is None:
            raise KeyError(f"Message with key value of {key_value} could not be found")

        return msg.decode(bit_str)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display(self) -> None:
        """Print a human-readable summary of the protocol and all its messages.

        Prints the protocol name followed by the formatted table for every
        registered message. Useful for quickly inspecting the structure of a
        protocol at the REPL or in debug output.

        Examples:
            >>> proto.display()
            Protocol: MyProtocol
            ...
        """
        print(f"Protocol: {self.name}")
        for _, msg in self.messages.items():
            print(msg)

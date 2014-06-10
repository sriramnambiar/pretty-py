import types
from collections import OrderedDict

__all__ = [
    "Symbol", "Field", "Record",
    "format", "display"
]


#
# Symbol, Field, Record
#

class Symbol(object) :
    def __init__(self, name) :
        self.name = name

    def __str__(self) :
        return "Symbol(%s)" % (repr(self.name),)

class Field(object) :
    def __init__(self, name, value) :
        self.name = name
        self.value = value

    def __str__(self) :
        return "Field(%s, %s)" % (repr(self.name), repr(self.value))

class Record(object) :
    def __init__(self, name, fields, opener="(", closer=")") :
        self.name = name
        self.fields = fields
        self.opener = opener
        self.closer = closer

    def __str__(self) :
        return "Record%s%s, %s%s" % (
            self.opener,
            repr(self.name),
            repr(self.fields),
            self.closer
        )


#
# Flex
#

class Flex(object) :
    def __init__(self, head, items, tail) :
        self.head = head
        self.items = items
        self.tail = tail


#
# FlexMaker
#

class FlexMaker(object) :
    def __init__(self) :
        self._processing = set()
        self._primitive_types = (
            types.NoneType,
            types.BooleanType,
            types.IntType, types.LongType,
            types.FloatType,
            types.StringType, types.UnicodeType,
            types.FunctionType,
            types.TypeType
        )

    def make(self, x) :
        t = type(x)
        if t in self._primitive_types :
            return repr(x)

        value_id = id(x)
        if value_id in self._processing :
            return "<ERROR:cycle>"
        self._processing.add(value_id)

        result = None
        if hasattr(x, "to_pretty") :
            result = self.make(x.to_pretty())
        elif t is Symbol :
            result = x.name
        elif t is Record :
            items = [self.make(f) for f in x.fields]
            result = Flex(x.name + x.opener, items, x.closer)
        elif t is Field :
            head = x.name + ": "
            inner = self.make(x.value)
            t2 = type(inner)
            if t2 is types.StringType :
                result = head + inner
            elif t2 is Flex :
                head += inner.head
                result = Flex(head, inner.items, inner.tail)
            else :
                assert False
        elif t is types.TupleType :
            items = [self.make(y) for y in x]
            result = Flex("(", items, ")")
        elif t is types.ListType :
            items = [self.make(y) for y in x]
            result = Flex("[", items, "]")
        elif t is set :
            items = [self.make(y) for y in x]
            result = Flex("set(", items, ")")
        elif t in (types.DictType, OrderedDict) :
            items = []
            for k, v in x.items() :
                f = Field(repr(k), self.make(v))
                items.append(self.make(f))
            result = Flex("{", items, "}")
        else :
            result = repr(x)

        self._processing.remove(value_id)
        return result


#
# OutputBuilder
#

class OutputBuilder(object) :
    def __init__(self) :
        self._lines = []
        self._current = []
        self._current_size = 0

    def lines(self) :
        return self._lines

    def current_size(self) :
        return self._current_size

    def add(self, s) :
        self._current.append(s)
        self._current_size += len(s)

    def new_line(self) :
        self._lines.append("".join(self._current))
        self._current = []
        self._current_size = 0


#
# Formatter
#

class Formatter(object) :
    def __init__(self, indent_unit="    ") :
        self._indent_unit = indent_unit

    def total_width(self, x) :
        t = type(x)
        if t is types.StringType :
            return len(x)
        assert t is Flex
        return len(x.head) + self.body_width(x) + len(x.tail)

    def body_width(self, x) :
        assert type(x) is Flex
        w = 0
        first = True
        for y in x.items :
            if first :
                first = False
            else :
                w += 2
            w += self.total_width(y)
        return w

    def new_line(self, output, level) :
        output.new_line()
        for _ in range(level) :
            output.add(self._indent_unit)

    def position_for_level(self, level) :
        return level * len(self._indent_unit)

    def format(self, x, output, level, max_width, following_multiline) :
        multiline = False
        w = self.total_width(x)
        position = output.current_size()
        if position > self.position_for_level(level) :
            if following_multiline or (w + 2 > max_width - position) :
                output.add(",")
                self.new_line(output, level)
                multiline = self.format(x, output, level, max_width, False)
            else :
                output.add(", ")
                self.format_single_line(x, output)
        elif type(x) is types.StringType :
            output.add(x)
        elif w <= max_width - position :
            self.format_single_line(x, output)
        else :
            output.add(x.head)
            if len(x.items) > 0 :
                self.new_line(output, level+1)
                last_was_multiline = False
                for y in x.items :
                    last_was_multiline = self.format(
                        y, output, level + 1, max_width, last_was_multiline
                    )
            self.new_line(output, level)
            output.add(x.tail)
            multiline = True
        return multiline

    def format_single_line(self, x, output) :
        t = type(x)
        if t is types.StringType :
            output.add(x)
        elif t is Flex :
            output.add(x.head)
            first = True
            for y in x.items :
                if first :
                    first = False
                else :
                    output.add(", ")
                self.format_single_line(y, output)
            output.add(x.tail)
        else :
            assert False


#
# format, print
#

def to_string(x) :
    flex_maker = FlexMaker()
    flex = flex_maker.make(x)
    output = OutputBuilder()
    formatter = Formatter()
    formatter.format_single_line(flex, output)
    output.new_line()
    lines = output.lines()
    assert len(lines) == 1
    return lines[0]

def format(x, max_width=78, indent_unit="    ") :
    flex_maker = FlexMaker()
    flex = flex_maker.make(x)
    output = OutputBuilder()
    formatter = Formatter(indent_unit)
    formatter.format(flex, output, 0, max_width, False)
    output.new_line()
    return output.lines()

def display(x, max_width=78, indent_unit="    ") :
    lines = format(x, max_width, indent_unit)
    for line in lines :
        print line

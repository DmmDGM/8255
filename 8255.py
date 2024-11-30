# Copyright (c) 2024-2025 iiPython

# Modules
import re
import sys
import operator
from enum import Enum
from pathlib import Path
from dataclasses import dataclass

# Exceptions
class NotAllocated(Exception):
    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name
    
    def __str__(self) -> str:
        return f"the specified variable '{self.variable_name}' has not yet been allocated"

class NullDataInOperation(Exception):
    def __str__(self) -> str:
        return "the specified range contains null data"

class ReservedName(Exception):
    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name

    def __str__(self) -> str:
        return f"the specified name ({self.variable_name}) is reserved"

# Typing
class ComparisonResult(Enum):
    EQUAL               = 1
    NOTEQUAL            = 2
    GREATERTHAN         = 3
    LESSTHAN            = 4
    GREATERTHENOREQUAL  = 5
    LESSTHANOREQUAL     = 6

class DataType(Enum):
    INTEGER = 1
    STRING  = 2
    NOTSET  = 3

@dataclass
class Allocation:
    start:  int
    end:    int
    size:   int

@dataclass
class Variable:
    allocation: Allocation
    datatype:   DataType

jump_mapping = {
    "jeq": ComparisonResult.EQUAL, "jnq": ComparisonResult.NOTEQUAL,
    "jgt": ComparisonResult.GREATERTHAN, "jlt": ComparisonResult.LESSTHAN,
    "jge": ComparisonResult.GREATERTHENOREQUAL, "jle": ComparisonResult.LESSTHANOREQUAL
}

# Handle buffering system
class Buffer:
    def __init__(self, size: int) -> None:
        self.size:  int = size
        self.vars:  dict[str, Variable] = {}
        self.store: list[None | int] = [None] * size
        self.predefined: dict[str, int] = {}

    def serialize(self, value: str | int, size: int) -> list[int]:
        if isinstance(value, int):
            return list(value.to_bytes(size))

        string_value = list(value.encode("ascii"))
        return string_value + [0] * (size - len(string_value))

    def allocate(self, size: int) -> Allocation:
        count, start_index = 0, -1
        for i, item in enumerate(self.store):
            if item is None:
                if count == 0:
                    start_index = i

                count += 1
                if count == size:
                    return Allocation(start_index, start_index + size - 1, size)

            else:
                count = 0

        raise MemoryError("out of memory to store object")

    def write(self, allocation: Allocation, value: str | int) -> None:
        serialized_value = self.serialize(value, allocation.size)
        if len(serialized_value) > allocation.size:
            raise OverflowError(f"requested value {repr(value)} ({len(serialized_value)} bytes) exceeds allocated memory size of {allocation.size} bytes")
        
        if allocation.end - 1 > self.size:
            raise OverflowError(f"requested value {repr(value)} ({len(serialized_value)} bytes) exceeds buffer size of {self.size} bytes")

        for index, value in enumerate(serialized_value):
            self.store[index + allocation.start] = value

    def get(self, allocation: Allocation, cast: DataType) -> str | int:
        value = self.store[allocation.start:allocation.end + 1]
        if any(b is None for b in value):
            raise NullDataInOperation

        match cast:
            case DataType.INTEGER:
                return int.from_bytes(bytes(value))  # type: ignore | Handled by the any() check above

            case DataType.STRING:
                return bytes(v for v in value if v).decode("ascii")  # type: ignore | Handled by the any() check above

            case _ as default:  # DataType.UNSET is not supported for these operations
                raise KeyError(default)

    def drop(self, allocation: Allocation) -> None:
        self.store[allocation.start:allocation.end + 1] = [None] * allocation.size

    # Handle variables
    def allocate_variable(self, name: str, size: int) -> None:
        if name in self.vars:
            raise ValueError("specified variable has already been allocated to the stack")

        self.vars[name] = Variable(self.allocate(size), DataType.NOTSET)

    def write_variable(self, name: str, value: str | int) -> None:
        if name in ["SLX", "SLY", "SLZ"]:
            raise ReservedName(name)

        if name not in self.vars:
            raise NotAllocated(name)

        self.vars[name].datatype = DataType.INTEGER if isinstance(value, int) else DataType.STRING
        self.write(self.vars[name].allocation, value)

    def get_variable(self, name: str) -> str | int:
        if name in self.predefined:
            return self.predefined[name]

        if name not in self.vars:
            raise NotAllocated(name)

        if self.vars[name].datatype == DataType.NOTSET:
            raise NullDataInOperation

        return self.get(self.vars[name].allocation, self.vars[name].datatype)

    def drop_variable(self, name: str) -> None:
        if name not in self.vars:
            raise NotAllocated(name)

        self.drop(self.vars[name].allocation)

    def write_predefined(self, name: str, value: int) -> None:
        self.predefined[name] = value

# Regex assignments
line_regex = re.compile(r"\"[^\"]*\"|\S+")
variable_regex = re.compile(r"\&(\w+)")
allocation_regex = re.compile(r":\[(\d+)\]")
string_sub_regex = re.compile(r"(\$\w+)")

# Handle loading file
def process_file(filepath: Path) -> None:
    file_lines = [
        line.strip() for line in filepath.read_text().splitlines()
        if line.strip()
    ]

    # Locate directives and process them
    blocked, last_line, file_size, line_data, labels = False, 0, 8192, [], {}
    for index, line in enumerate(file_lines):
        line = re.findall(line_regex, line.split("//")[0])
        if line == ["."]:
            if not blocked:
                raise SyntaxError("cannot use . directive without active code block")

            if index != len(file_lines) - 1:
                raise SyntaxError("the . directive must be at end of file")

            continue

        if line[0].isdigit():
            if file_lines[index - 1] != "START" and not blocked:
                raise SyntaxError("cannot begin code block without START directive")

            blocked = True

            # Check line numbers add up
            line_number = int(line[0])
            if line_number != last_line + 10:
                raise SyntaxError("line numbers must be multiples of 10")

            last_line = line_number

            # Check for extras
            match line[1:]:
                case ["lbl", label_name]:
                    labels[label_name] = len(line_data)

            line_data.append(line[1:])
            continue

        elif blocked:
            raise SyntaxError("cannot have a directive inside the code block")

        # Process directives
        match line:
            case ["PROGRAM", _] | ["START"]:
                pass  # Valid, but not used

            case ["SIZE", size, "BINARY" | "DECIMAL" as data_format]:
                size_match = re.match(r"(1|2|4|8|16|32|64|128)K", size)
                if not size_match:
                    raise SyntaxError("specified size directive has an invalid size argument")

                file_size = int(size_match.group(1)) * (1024 if data_format == "BINARY" else 1000)

            case _ as default:
                raise SyntaxError(f"invalid or unknown directive: {default}")

    # Initialize buffer
    buffer = Buffer(file_size)

    # Handle values
    def process_value(value: str) -> str | int:
        if value[0] == "&":
            if not value[1:]:
                raise SyntaxError

            return buffer.get_variable(value[1:])

        if value.isnumeric():
            return int(value)

        if not (value[0] == "\"" and value[-1] == "\"" and len(value) > 1):
            raise SyntaxError

        value = value.strip("\"")
        for variable in re.findall(string_sub_regex, value):
            value = value.replace(variable, str(buffer.get_variable(variable[1:])))

        return value

    def handle_variable(variable: str, regex: re.Pattern = variable_regex) -> str:
        variable_match = re.match(regex, variable)
        if not variable_match:
            raise SyntaxError

        return variable_match.group(1)

    # Handle iteration
    current_line, comparison_result = 0, None
    while current_line <= len(line_data) - 1:
        try:
            match line_data[current_line]:
                case ["out", message]:
                    print(process_value(message))

                case ["lbl", _]:
                    pass

                case ["alc", variable, allocation]:
                    buffer.allocate_variable(
                        handle_variable(variable),
                        int(handle_variable(allocation, allocation_regex))
                    )

                case ["inp", prompt, ">", variable]:
                    value = process_value(prompt)
                    if not isinstance(value, str):
                        raise ValueError("argument to inp must be a STRING")

                    buffer.write_variable(handle_variable(variable), input(value))

                case ["add" | "sub" | "mul" | "div" | "pow" as operator_type, num1, num2, ">", variable]:
                    buffer.write_variable(
                        handle_variable(variable),
                        getattr(operator, operator_type if operator_type != "div" else "truediv")(process_value(num1), process_value(num2))
                    )

                case ["cst", variable, "STRING" | "INTEGER" as cast_type]:
                    variable = handle_variable(variable)
                    buffer.write_variable(
                        variable,
                        {"INTEGER": int, "STRING": str}[cast_type](buffer.get_variable(variable))
                    )

                case ["cmp", variable1, variable2]:
                    variable1, variable2 = process_value(variable1), process_value(variable2)
                    if variable1 == variable2:
                        comparison_result = ComparisonResult.EQUAL

                    elif variable1 != variable2:
                        comparison_result = ComparisonResult.NOTEQUAL

                    # Ensure our types are the same
                    elif type(variable1) is not type(variable2):
                            raise ValueError("comparison variable types must be same when using >/</>=/<=")

                    elif variable1 > variable2:  # type: ignore | Checked above
                        comparison_result = ComparisonResult.GREATERTHAN

                    elif variable1 < variable2:  # type: ignore | Checked above
                        comparison_result = ComparisonResult.LESSTHAN

                    elif variable1 >= variable2:  # type: ignore | Checked above
                        comparison_result = ComparisonResult.GREATERTHENOREQUAL

                    elif variable1 <= variable2:  # type: ignore | Checked above
                        comparison_result = ComparisonResult.LESSTHANOREQUAL

                case ["jeq" | "jnq" | "jgt" | "jlt" | "jge" | "jle" as jump_type, label]:
                    if comparison_result == jump_mapping[jump_type]:
                        current_line = labels[label]
                        continue

                case ["drp", variable]:
                    buffer.drop_variable(handle_variable(variable))

                case _ as default:
                    raise SyntaxError(default)

        except Exception as e:
            if isinstance(e, (NotAllocated, NullDataInOperation, OverflowError)):
                raise e

            buffer.write_predefined("slx", 1)
            current_line += 1
            continue

        buffer.write_predefined("slx", 0)
        current_line += 1

if __name__ == "__main__":
    process_file(Path(sys.argv[1]))

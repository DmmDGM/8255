# Copyright (c) 2024-2025 iiPython

# Modules
from enum import Enum
from dataclasses import dataclass

# Exceptions
class StackError(Exception):
    pass

class NotAllocated(StackError):
    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name
    
    def __str__(self) -> str:
        return f"the specified variable '{self.variable_name}' has not yet been allocated"

class NullDataInOperation(StackError):
    def __str__(self) -> str:
        return "the specified range contains null data"

class ReservedName(StackError):
    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name

    def __str__(self) -> str:
        return f"the specified name ({self.variable_name}) is reserved"

class MemoryOverflow(StackError):
    pass

# Typing
ALLOCATED = b"\x00"  # Might change eventually

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
class Register:
    allocation: Allocation
    datatype:   DataType

@dataclass
class ReservedRegister:
    value:  int

# Handle the stack :3
class Stack:
    def __init__(self, size: int) -> None:
        self.size:  int = size
        self.vars:  dict[str, Register | ReservedRegister] = {
            "slx": ReservedRegister(0),
            "sly": ReservedRegister(0),
            "slz": ReservedRegister(0),
        }
        self.store: list[None | int | bytes] = [None] * size

    def serialize(self, value: str | int, size: int) -> list[int]:
        if isinstance(value, int):
            return list(value.to_bytes(size, signed = True))

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
                    self.store[start_index:start_index + size] = [ALLOCATED] * size
                    return Allocation(start_index, start_index + size - 1, size)

            else:
                count = 0

        raise MemoryOverflow("out of memory to store object")

    def write(self, allocation: Allocation, value: str | int) -> None:
        serialized_value = self.serialize(value, allocation.size)
        if len(serialized_value) > allocation.size:
            raise MemoryOverflow(f"requested value {repr(value)} ({len(serialized_value)} bytes) exceeds allocated memory size of {allocation.size} bytes")
        
        if allocation.end - 1 > self.size:
            raise MemoryOverflow(f"requested value {repr(value)} ({len(serialized_value)} bytes) exceeds buffer size of {self.size} bytes")

        self.store[allocation.start:allocation.end + 1] = serialized_value

    def get(self, allocation: Allocation, cast: DataType) -> str | int:
        value = self.store[allocation.start:allocation.end + 1]
        if any(b is None for b in value):
            raise NullDataInOperation

        match cast:
            case DataType.INTEGER:
                return int.from_bytes(bytes(value), signed = True)  # type: ignore | Handled by the any() check above

            case DataType.STRING:
                return bytes(v for v in value if v).decode("ascii")  # type: ignore | Handled by the any() check above

            case DataType.NOTSET:  # DataType.NOTSET is not supported for these operations
                raise StackError("NOTSET datatype is not valid for get operations")

    def drop(self, allocation: Allocation) -> None:
        self.store[allocation.start:allocation.end + 1] = [None] * allocation.size

    # Handle variables
    def allocate_variable(self, name: str, size: int) -> None:
        if name in self.vars:
            raise ValueError("specified variable has already been allocated to the stack")

        self.vars[name] = Register(self.allocate(size), DataType.NOTSET)

    def write_variable(self, name: str, value: str | int, reserved: bool = False) -> None:
        if name not in self.vars:
            raise NotAllocated(name)

        if isinstance(self.vars[name], ReservedRegister):
            if not reserved:
                raise ReservedName(name)

            self.vars[name].value = value  # pyright: ignore
            return

        # Pyright is retarded... the following lines are safe due to the
        # isinstance() check right above us
        self.vars[name].datatype = DataType.INTEGER if isinstance(value, int) else DataType.STRING  # pyright: ignore
        self.write(self.vars[name].allocation, value)  # pyright: ignore

    def get_variable(self, name: str) -> str | int:
        if name not in self.vars:
            raise NotAllocated(name)

        if isinstance(self.vars[name], ReservedRegister):
            return self.vars[name].value  # pyright: ignore

        if self.vars[name].datatype == DataType.NOTSET:  # pyright: ignore
            raise NullDataInOperation

        return self.get(self.vars[name].allocation, self.vars[name].datatype)  # pyright: ignore

    def drop_variable(self, name: str) -> None:
        if name not in self.vars:
            raise NotAllocated(name)

        if isinstance(self.vars[name], ReservedRegister):
            raise ReservedName(name)

        self.drop(self.vars[name].allocation)  # pyright: ignore
        del self.vars[name]

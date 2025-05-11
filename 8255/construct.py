# Copyright (c) 2024-2025 iiPython

import re
from dataclasses import dataclass

LINE_REGEX = re.compile(r"\"[^\"]*\"|\S+")
SIZE_SYSTEM_MAPPING = {
    "BINARY":  1024,
    "BIN":     1024,
    "DECIMAL": 1000,
    "DEC":     1000
}

@dataclass
class Program:
    name:       str
    """The name of this program."""
    byte_size:  int
    """The byte size of the stack for this program."""
    lines:      list[list[str]]
    """The parsed line data for this program."""
    labels:     dict[str, int]
    """Label mappings for this program."""

def process_lines(lines: list[str]) -> list[list[str]]:
    """Taking in unprocessed lines, remove comments and return the parsed version."""
    processed_lines = []
    for line in lines:
        line = re.findall(LINE_REGEX, line)
        processed_lines.append(line[:line.index("//")] if "//" in line else line)

    return processed_lines

def construct_program(lines: list[str]) -> Program:
    processed_lines = process_lines(lines)
    program = {"name": None, "byte_size": 8192, "lines": [], "labels": {}}
    in_code_block, last_line = False, 0
    for index, line in enumerate(processed_lines):
        match line:
            case ["START"] if not in_code_block:
                pass

            case ["PROGRAM", program_name] if not in_code_block:
                program["name"] = program_name.strip("\"")

            case ["SIZE", size, system] if not in_code_block:
                size_match = re.match(r"(1|2|4|8|16|32|64|128)K", size)
                if not size_match:
                    raise SyntaxError("specified size directive has an invalid size argument")

                if system not in SIZE_SYSTEM_MAPPING:
                    raise SyntaxError("specified system for size directive is incorrect")

                program["byte_size"] = int(size_match.group(1)) * SIZE_SYSTEM_MAPPING[system]

            case ["."]:
                if not in_code_block:
                    raise SyntaxError("cannot use . directive without active code block")

                if index != len(processed_lines) - 1:
                    raise SyntaxError("the . directive must be at end of file")

            case [line_number, *code_line]:
                if not line_number.isnumeric():
                    raise SyntaxError("cannot have a directive inside the code block")

                if processed_lines[index - 1] != ["START"] and not in_code_block:
                    raise SyntaxError("cannot begin code block without START directive")

                # Check line numbers add up
                if int(line_number) <= last_line or int(line_number) % 10:
                    raise SyntaxError("line numbers must be increasing in multiples of 10")

                last_line = int(line_number)

                # Handle basic line parsing
                match code_line:
                    case ["lbl", label_name]:
                        program["labels"][label_name] = len(program["lines"])

                # Push to lines
                in_code_block = True
                program["lines"].append(code_line)

            case _ as default:
                raise Exception(f"Something didn't match! {default}")

    return Program(**program)

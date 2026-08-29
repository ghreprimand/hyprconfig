"""Small JSON-with-comments validator for bundled and user Waybar configs."""

import json
import re


def strip_comments(text):
    output = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
        elif char == "/" and following == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
        elif char == "/" and following == "*":
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != "*/":
                index += 1
            index += 2
        else:
            output.append(char)
            index += 1
    return "".join(output)


def loads(text):
    without_comments = strip_comments(text)
    without_trailing_commas = re.sub(r",\s*([}\]])", r"\1", without_comments)
    return json.loads(without_trailing_commas)

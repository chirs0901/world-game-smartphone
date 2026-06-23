"""Structured output parsing utilities for LLM responses."""

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from src.utils.logging import logger

T = TypeVar("T", bound=BaseModel)


def extract_json_from_text(text: str) -> dict | list:
    """Extract JSON from LLM response text.

    Handles common cases:
    - Plain JSON
    - JSON wrapped in markdown code blocks (```json ... ```)
    - JSON embedded in surrounding text
    """
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object or array boundaries
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Find the matching closing bracket
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}...")


def parse_structured_output(text: str, schema: type[T]) -> T:
    """Parse LLM response text into a Pydantic model.

    Args:
        text: Raw LLM response text
        schema: Pydantic model class to parse into

    Returns:
        Parsed model instance

    Raises:
        ValueError: If JSON extraction or Pydantic validation fails
    """
    data = extract_json_from_text(text)
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        logger.warning("Pydantic validation failed", error=str(e), data_keys=list(data.keys()) if isinstance(data, dict) else "not_dict")
        raise ValueError(f"Schema validation failed: {e}") from e


def build_json_schema_hint(schema: type[BaseModel]) -> str:
    """Generate a JSON schema hint string to append to the system prompt."""
    schema_json = schema.model_json_schema()
    return f"\n\n输出必须严格符合以下 JSON Schema：\n```json\n{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n```"

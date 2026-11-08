"""Experimental, runtime-neutral CliffCompaction transformation.

The implementation follows Algorithm 1 from Nguyen et al., "CliffCompaction:
Cost-Efficient Compaction for Long-Horizon Coding Agents" (2026). Runtime
adapters remain responsible for token counting, deciding when to trigger, and
translating the projection into a provider-specific message schema.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

Role: TypeAlias = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class TextPart:
    """Visible natural-language content."""

    text: str


@dataclass(frozen=True, slots=True)
class ReasoningPart:
    """Model analysis, planning, or hypotheses that may be truncated."""

    text: str


@dataclass(frozen=True, slots=True)
class ToolCallPart:
    """A normalized tool call with adapter-selected, ordered arguments.

    Adapters should place essential, recoverability-relevant arguments first
    and render nested runtime values into deterministic strings.
    """

    name: str
    arguments: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        argument_names = [name for name, _ in self.arguments]
        if len(argument_names) != len(set(argument_names)):
            raise ValueError("tool-call argument names must be unique")


@dataclass(frozen=True, slots=True)
class ToolResultPart:
    """A tool observation returned to the model."""

    content: str
    tool_name: str = ""


@dataclass(frozen=True, slots=True)
class CompactionPart:
    """A harness-created compacted block, never an original model turn."""

    content: str
    generation: int


Part: TypeAlias = TextPart | ReasoningPart | ToolCallPart | ToolResultPart | CompactionPart


@dataclass(frozen=True, slots=True)
class Message:
    """Runtime-neutral model-facing message."""

    role: Role
    parts: tuple[Part, ...]


@dataclass(frozen=True, slots=True)
class CliffConfig:
    """Deterministic compaction policy.

    The three character limits are the values in Algorithm 1 of the paper.
    ``recent_turn_pairs`` is required because the paper leaves K symbolic and
    evaluates multiple runtime-specific context budgets rather than declaring
    a universal K.
    """

    recent_turn_pairs: int
    tool_result_max_chars: int = 500
    tool_signature_max_chars: int = 150
    reasoning_max_chars: int = 300

    def __post_init__(self) -> None:
        values = {
            "recent_turn_pairs": self.recent_turn_pairs,
            "tool_result_max_chars": self.tool_result_max_chars,
            "tool_signature_max_chars": self.tool_signature_max_chars,
            "reasoning_max_chars": self.reasoning_max_chars,
        }
        for name, value in values.items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class CompactionMetadata:
    """Bounded evidence emitted with every projection."""

    algorithm: str
    status: str
    generation: int
    input_hash: str
    source_hash: str
    projection_hash: str
    source_message_count: int
    old_message_count: int
    recent_message_count: int
    source_part_count: int
    retained_part_count: int
    dropped_part_count: int
    prior_compaction_message_count: int
    tool_result_retained_count: int
    tool_result_dropped_count: int
    tool_call_reduced_count: int
    reasoning_truncated_count: int


@dataclass(frozen=True, slots=True)
class CompactionResult:
    """A model-facing projection plus deterministic evaluation metadata."""

    messages: tuple[Message, ...]
    config: CliffConfig
    metadata: CompactionMetadata


def stable_serialize_messages(messages: Sequence[Message]) -> str:
    """Serialize messages with a stable schema and deterministic key order."""
    data = [_message_data(message) for message in messages]
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def compact(messages: Sequence[Message], config: CliffConfig) -> CompactionResult:
    """Create one Cliff projection without mutating the canonical transcript.

    The input must begin with one system message and the original user task,
    matching the paper's ``messages[0]`` and ``messages[1]`` contract. If a
    prior :class:`CompactionPart` exists, only messages after the latest such
    block are treated as the new live segment.
    """
    original = tuple(messages)
    _validate_prefix(original)

    prefix = original[:2]
    tail = original[2:]
    prior_indexes = [index for index, message in enumerate(tail) if _is_compaction(message)]
    prior_count = len(prior_indexes)
    previous_generation = _latest_generation(tail)

    live_start = prior_indexes[-1] + 1 if prior_indexes else 0
    live = tail[live_start:]
    recent_message_limit = config.recent_turn_pairs * 2
    old_count = max(0, len(live) - recent_message_limit)
    old = live[:old_count]
    recent = live[old_count:]

    fragments: list[str] = []
    retained_part_count = sum(len(message.parts) for message in recent)
    dropped_part_count = 0
    tool_result_retained_count = 0
    tool_result_dropped_count = 0
    tool_call_reduced_count = 0
    reasoning_truncated_count = 0

    for message in old:
        if _is_compaction(message):
            dropped_part_count += len(message.parts)
            continue

        if message.role == "assistant":
            remaining_reasoning = config.reasoning_max_chars
            for part in message.parts:
                if isinstance(part, (TextPart, ReasoningPart)):
                    retained = part.text[:remaining_reasoning]
                    if retained:
                        fragments.append(retained)
                        retained_part_count += 1
                    else:
                        dropped_part_count += 1
                    if len(part.text) > len(retained):
                        reasoning_truncated_count += 1
                    remaining_reasoning -= len(retained)
                elif isinstance(part, ToolCallPart):
                    signature = _tool_signature(part, config.tool_signature_max_chars)
                    if signature:
                        fragments.append(signature)
                        retained_part_count += 1
                    else:
                        dropped_part_count += 1
                    tool_call_reduced_count += 1
                else:
                    dropped_part_count += 1
            continue

        if message.role == "tool":
            for part in message.parts:
                if isinstance(part, ToolResultPart):
                    if len(part.content) <= config.tool_result_max_chars:
                        fragments.append(part.content)
                        retained_part_count += 1
                        tool_result_retained_count += 1
                    else:
                        dropped_part_count += 1
                        tool_result_dropped_count += 1
                else:
                    dropped_part_count += 1
            continue

        dropped_part_count += len(message.parts)

    generation = previous_generation + 1
    block = Message(
        role="assistant",
        parts=(CompactionPart(content="\n".join(fragments), generation=generation),),
    )
    projection = prefix + (block,) + recent
    source_part_count = sum(len(message.parts) for message in live)

    metadata = CompactionMetadata(
        algorithm="cliff-compaction-v1",
        status="experimental",
        generation=generation,
        input_hash=_hash_messages(original),
        source_hash=_hash_messages(live),
        projection_hash=_hash_messages(projection),
        source_message_count=len(live),
        old_message_count=len(old),
        recent_message_count=len(recent),
        source_part_count=source_part_count,
        retained_part_count=retained_part_count,
        dropped_part_count=dropped_part_count,
        prior_compaction_message_count=prior_count,
        tool_result_retained_count=tool_result_retained_count,
        tool_result_dropped_count=tool_result_dropped_count,
        tool_call_reduced_count=tool_call_reduced_count,
        reasoning_truncated_count=reasoning_truncated_count,
    )
    return CompactionResult(messages=projection, config=config, metadata=metadata)


def _validate_prefix(messages: tuple[Message, ...]) -> None:
    if len(messages) < 2 or messages[0].role != "system" or messages[1].role != "user":
        raise ValueError("messages must begin with a system message and original user task")


def _is_compaction(message: Message) -> bool:
    return any(isinstance(part, CompactionPart) for part in message.parts)


def _latest_generation(messages: Sequence[Message]) -> int:
    generations = [
        part.generation
        for message in messages
        for part in message.parts
        if isinstance(part, CompactionPart)
    ]
    return max(generations, default=0)


def _tool_signature(part: ToolCallPart, max_chars: int) -> str:
    arguments = {name: value for name, value in part.arguments}
    rendered_arguments = json.dumps(
        arguments,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"[{part.name}] {rendered_arguments}"[:max_chars]


def _hash_messages(messages: Sequence[Message]) -> str:
    serialized = stable_serialize_messages(messages)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _message_data(message: Message) -> dict[str, object]:
    return {
        "role": message.role,
        "parts": [_part_data(part) for part in message.parts],
    }


def _part_data(part: Part) -> dict[str, object]:
    if isinstance(part, TextPart):
        return {"kind": "text", "text": part.text}
    if isinstance(part, ReasoningPart):
        return {"kind": "reasoning", "text": part.text}
    if isinstance(part, ToolCallPart):
        return {
            "kind": "tool_call",
            "name": part.name,
            "arguments": [
                {"name": name, "value": value} for name, value in part.arguments
            ],
        }
    if isinstance(part, ToolResultPart):
        return {
            "kind": "tool_result",
            "tool_name": part.tool_name,
            "content": part.content,
        }
    return {
        "kind": "compaction",
        "generation": part.generation,
        "content": part.content,
    }

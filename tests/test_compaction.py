from __future__ import annotations

from awesome_harness.compaction import (
    CliffConfig,
    CompactionPart,
    Message,
    ReasoningPart,
    TextPart,
    ToolCallPart,
    ToolResultPart,
    compact,
    stable_serialize_messages,
)


def _prefix() -> tuple[Message, Message]:
    return (
        Message("system", (TextPart("system instructions"),)),
        Message("user", (TextPart("original task"),)),
    )


def _block(result_messages: tuple[Message, ...]) -> CompactionPart:
    part = result_messages[2].parts[0]
    assert isinstance(part, CompactionPart)
    return part


def test_cliff_applies_every_paper_rule_and_preserves_recent_pair() -> None:
    long_reasoning = "r" * 350
    long_inline_content = "content=" + ("x" * 300)
    small_result = "exit code: 0"
    large_result = "z" * 501
    recent_user = Message("user", (TextPart("latest request"),))
    recent_assistant = Message("assistant", (ReasoningPart("latest answer"),))
    source = _prefix() + (
        Message(
            "assistant",
            (
                ReasoningPart(long_reasoning),
                ToolCallPart(
                    "write_file",
                    (("path", "src/app.py"), ("content", long_inline_content)),
                ),
            ),
        ),
        Message("tool", (ToolResultPart(small_result, "shell"),)),
        Message("tool", (ToolResultPart(large_result, "read_file"),)),
        Message("user", (TextPart("old follow-up that should be dropped"),)),
        recent_user,
        recent_assistant,
    )

    result = compact(source, CliffConfig(recent_turn_pairs=1))
    block = _block(result.messages)

    assert result.messages[:2] == source[:2]
    assert result.messages[-2:] == (recent_user, recent_assistant)
    assert long_reasoning[:300] in block.content
    assert long_reasoning not in block.content
    assert small_result in block.content
    assert large_result not in block.content
    assert "old follow-up" not in block.content
    signature = next(line for line in block.content.splitlines() if line.startswith("[write_file]"))
    assert len(signature) == 150
    assert signature.startswith('[write_file] {"path":"src/app.py"')
    assert long_inline_content not in signature

    metadata = result.metadata
    assert metadata.status == "experimental"
    assert metadata.tool_result_retained_count == 1
    assert metadata.tool_result_dropped_count == 1
    assert metadata.tool_call_reduced_count == 1
    assert metadata.reasoning_truncated_count == 1
    assert metadata.old_message_count == 4
    assert metadata.recent_message_count == 2
    assert metadata.retained_part_count + metadata.dropped_part_count == metadata.source_part_count


def test_tool_result_cutoff_is_inclusive_and_configurable() -> None:
    source = _prefix() + (
        Message("tool", (ToolResultPart("a" * 4),)),
        Message("tool", (ToolResultPart("b" * 5),)),
    )

    result = compact(
        source,
        CliffConfig(recent_turn_pairs=0, tool_result_max_chars=4),
    )

    assert "a" * 4 in _block(result.messages).content
    assert "b" * 5 not in _block(result.messages).content
    assert result.metadata.tool_result_retained_count == 1
    assert result.metadata.tool_result_dropped_count == 1


def test_compaction_is_deterministic_and_serialization_preserves_argument_order() -> None:
    source = _prefix() + (
        Message(
            "assistant",
            (ToolCallPart("read", (("path", "b.py"), ("line", "12"))),),
        ),
    )
    config = CliffConfig(recent_turn_pairs=0)

    first = compact(source, config)
    second = compact(source, config)
    serialized = stable_serialize_messages(first.messages)

    assert first == second
    assert first.metadata.input_hash.startswith("sha256:")
    assert first.metadata.source_hash.startswith("sha256:")
    assert first.metadata.projection_hash.startswith("sha256:")
    assert first.metadata.projection_hash == second.metadata.projection_hash
    assert serialized == stable_serialize_messages(second.messages)
    assert _block(first.messages).content.index('"path":"b.py"') < _block(
        first.messages
    ).content.index('"line":"12"')


def test_second_cliff_discards_prior_block_and_compacts_only_live_segment() -> None:
    first_source = _prefix() + (
        Message("assistant", (ReasoningPart("first-old-secret"),)),
        Message("tool", (ToolResultPart("first recent tool result"),)),
        Message("assistant", (ReasoningPart("first recent answer"),)),
    )
    first = compact(first_source, CliffConfig(recent_turn_pairs=1))
    first_block = _block(first.messages)
    live_after_first = (
        Message("assistant", (ReasoningPart("second-window-old"),)),
        Message("user", (TextPart("second recent request"),)),
        Message("assistant", (ReasoningPart("second recent answer"),)),
    )

    second = compact(
        first.messages + live_after_first,
        CliffConfig(recent_turn_pairs=1),
    )
    second_block = _block(second.messages)

    assert second_block.generation == 2
    assert first_block.content not in second_block.content
    assert "first-old-secret" not in second_block.content
    assert "first recent tool result" in second_block.content
    assert "first recent answer" in second_block.content
    assert "second-window-old" in second_block.content
    assert second.messages[-2:] == live_after_first[-2:]
    assert second.metadata.prior_compaction_message_count == 1
    assert second.metadata.source_message_count == 5


def test_compaction_does_not_mutate_original_messages() -> None:
    source = _prefix() + (
        Message("assistant", (ReasoningPart("r" * 400),)),
        Message("tool", (ToolResultPart("output"),)),
    )
    before = stable_serialize_messages(source)

    compact(source, CliffConfig(recent_turn_pairs=0))

    assert stable_serialize_messages(source) == before


def test_invalid_prefix_and_negative_configuration_are_rejected() -> None:
    try:
        CliffConfig(recent_turn_pairs=-1)
    except ValueError as error:
        assert "recent_turn_pairs" in str(error)
    else:
        raise AssertionError("negative recent-turn count must fail")

    try:
        compact((Message("user", (TextPart("task"),)),), CliffConfig(recent_turn_pairs=0))
    except ValueError as error:
        assert "system message" in str(error)
    else:
        raise AssertionError("missing canonical prefix must fail")

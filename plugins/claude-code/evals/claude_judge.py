"""Single-turn judge calls through the Claude Code CLI (claude-agent-sdk).

The judge authenticates the same way the live-eval agent does: with the local
`claude` login. No Anthropic API key is needed.
"""

import asyncio

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query


class JudgeError(RuntimeError):
    """The judge produced no usable verdict (CLI error, empty or unparseable reply)."""


def judge_options(system: str, model: str) -> ClaudeAgentOptions:
    """Options for a bare completion: no tools, no MCP servers, no user or project settings."""
    return ClaudeAgentOptions(
        system_prompt=system,
        tools=[],
        max_turns=1,
        model=model,
        setting_sources=[],
        extra_args={"strict-mcp-config": None},
    )


async def ask(system: str, prompt: str, model: str) -> str:
    """Return the judge's reply text for one prompt.

    Raises JudgeError when the CLI reports an error (not logged in, rate limit, ...)
    or returns no text, so a broken judge fails the run instead of being scored.
    """
    parts: list[str] = []
    async for message in query(prompt=prompt, options=judge_options(system, model)):
        if isinstance(message, AssistantMessage):
            parts.extend(block.text for block in message.content if isinstance(block, TextBlock))
        elif isinstance(message, ResultMessage) and message.is_error:
            raise JudgeError(f"judge CLI error ({message.subtype}): {message.result or ' '.join(parts)}")
    reply = "\n".join(parts).strip()
    if not reply:
        raise JudgeError("judge returned an empty reply")
    return reply


def ask_sync(system: str, prompt: str, model: str) -> str:
    return asyncio.run(ask(system, prompt, model))

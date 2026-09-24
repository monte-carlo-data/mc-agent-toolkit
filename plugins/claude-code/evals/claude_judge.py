"""Single-turn judge calls through the Claude Code CLI (claude-agent-sdk).

The judge authenticates the same way the live-eval agent does: with the local
`claude` login. No Anthropic API key is needed.
"""

import asyncio

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query


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
    """Return the judge's reply text for one prompt."""
    parts: list[str] = []
    async for message in query(prompt=prompt, options=judge_options(system, model)):
        if isinstance(message, AssistantMessage):
            parts.extend(block.text for block in message.content if isinstance(block, TextBlock))
    return "\n".join(parts).strip()


def ask_sync(system: str, prompt: str, model: str) -> str:
    return asyncio.run(ask(system, prompt, model))

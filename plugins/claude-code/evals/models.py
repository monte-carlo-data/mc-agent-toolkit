"""Data models for live evals."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TurnCriteria:
    """Deterministic checks applied to a single turn's trace."""

    must_call: list[str] = field(default_factory=list)
    must_not_call: list[str] = field(default_factory=list)
    output_must_not_contain: list[str] = field(default_factory=list)
    # Substrings that must not appear in any tool call's input (e.g. a planted secret).
    tool_input_must_not_contain: list[str] = field(default_factory=list)
    # {earlier_tool: [later_tool, ...]}: each later tool, if called, must come after earlier_tool.
    must_call_before: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def _fields_from_dict(cls, data: dict) -> dict:
        return {
            "must_call": data.get("must_call", []),
            "must_not_call": data.get("must_not_call", []),
            "output_must_not_contain": data.get("output_must_not_contain", []),
            "tool_input_must_not_contain": data.get("tool_input_must_not_contain", []),
            "must_call_before": data.get("must_call_before", {}),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TurnCriteria":
        return cls(**cls._fields_from_dict(data))


@dataclass
class CaseCriteria(TurnCriteria):
    """Case-level criteria extends turn criteria with a judge rubric."""

    judge_rubric: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CaseCriteria":
        return cls(**cls._fields_from_dict(data), judge_rubric=data.get("judge_rubric", ""))


@dataclass
class Turn:
    prompt: str
    criteria: TurnCriteria = field(default_factory=TurnCriteria)

    @classmethod
    def from_dict(cls, data: dict) -> "Turn":
        return cls(
            prompt=data["prompt"],
            criteria=TurnCriteria.from_dict(data.get("criteria", {})),
        )


SURFACES = ("skill", "connector")


@dataclass
class EvalCase:
    id: str
    turns: list[Turn]
    criteria: CaseCriteria = field(default_factory=CaseCriteria)
    # "skill": SKILL.md is appended to the system prompt (plugin installed).
    # "connector": no skill content; guidance comes only from the MCP server.
    surface: str = "skill"

    @classmethod
    def from_dict(cls, data: dict) -> "EvalCase":
        turns = [Turn.from_dict(t) for t in data["turns"]]
        surface = data.get("surface", "skill")
        if surface not in SURFACES:
            raise ValueError(f"case {data['id']}: surface must be one of {SURFACES}, got {surface!r}")
        return cls(
            id=data["id"],
            turns=turns,
            criteria=CaseCriteria.from_dict(data.get("criteria", {})),
            surface=surface,
        )


@dataclass
class ConversationTrace:
    """Accumulated trace from one or more conversation turns."""

    tools_called: list[str] = field(default_factory=list)
    tool_details: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    stderr: list[str] = field(default_factory=list)
    final_text: str = ""
    # Every assistant text block, in order; final_text is only the last message.
    all_text: list[str] = field(default_factory=list)
    num_turns: int = 0
    total_cost_usd: float = 0.0
    session_id: str | None = None


@dataclass
class CaseResult:
    id: str
    passed: bool
    deterministic_passed: bool
    deterministic_failures: list[str]
    judge_score: float
    judge_reason: str
    tools_called: list[str]
    num_turns: int
    cost_usd: float
    final_text: str = ""
    tool_details: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    stderr: list[str] = field(default_factory=list)
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float = 0.0

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentTraceStep:
    tool: str
    ok: bool
    summary: str


@dataclass
class AgentTrace:
    steps: list[AgentTraceStep] = field(default_factory=list)
    truncated: bool = False

    def add(self, tool: str, ok: bool, summary: str) -> None:
        self.steps.append(AgentTraceStep(tool=tool, ok=ok, summary=summary))

    def to_list(self) -> list[AgentTraceStep]:
        return list(self.steps)

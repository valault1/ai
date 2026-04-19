from __future__ import annotations

from dataclasses import dataclass


class ScriptStep:
    """Subclass to define a deterministic, script-based pipeline step.

    Class attributes (set on subclass):
        id   (str): unique identifier within the pipeline
        name (str): human-readable display name

    Override:
        run(params, context) -> dict
        should_skip(params, context) -> bool   (optional)
        on_skip(params, context)               (optional, for side-effects on skip)
    """

    id: str
    name: str

    def run(self, params: dict, context: dict) -> dict:
        raise NotImplementedError

    def should_skip(self, params: dict, context: dict) -> bool:
        return False

    def on_skip(self, params: dict, context: dict) -> None:
        pass


class LLMStep:
    """Subclass to define a step that calls the Claude API.

    Class attributes (set on subclass):
        id            (str):        unique identifier within the pipeline
        name          (str):        human-readable display name
        model         (str):        Claude model ID
        output_schema (dict|None):  JSON Schema; if set, uses tool_use for structured output

    Override:
        build_messages(params, context) -> list[dict]   (Anthropic messages format)
        should_skip(params, context) -> bool            (optional)
        on_skip(params, context)                        (optional)
        post_run(params, context, output)               (optional, write canonical files etc.)
    """

    id: str
    name: str
    model: str = "claude-sonnet-4-6"
    output_schema: dict | None = None

    def build_messages(self, params: dict, context: dict) -> list[dict]:
        raise NotImplementedError

    def should_skip(self, params: dict, context: dict) -> bool:
        return False

    def on_skip(self, params: dict, context: dict) -> None:
        pass

    def post_run(self, params: dict, context: dict, output: dict) -> None:
        pass


@dataclass
class Pipeline:
    """A named sequence of steps, triggered with a dict of params."""

    id: str
    name: str
    params: list[str]           # e.g. ["ticker"]
    steps: list                 # ScriptStep | LLMStep instances

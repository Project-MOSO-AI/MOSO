import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from moso_core.pipelines.base import PipelineResult

logger = logging.getLogger(__name__)


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""
    matched_pattern: Optional[str] = None


class PromptGuard:
    INJECTION_PATTERNS: list[tuple[str, str]] = [
        (r"(?i)(ignore|disregard)\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|directions)", "prompt_injection"),
        (r"(?i)(you\s+are\s+now|new\s+role|act\s+as\s+if)", "role_redirection"),
        (r"(?i)system\s+prompt\s*:?", "system_prompt_leak"),
        (r"(?i)(reveal|show|display|print|output)\s+(your\s+)?(system\s+)?prompt", "prompt_leak"),
        (r"(?i)(forget|reset|clear)\s+(all\s+)?(instructions|training|constraints|guidelines)", "instruction_reset"),
        (r"(?i)(do\s+not\s+follow|ignore\s+(your\s+)?(guidelines|rules|policy))", "rule_override"),
    ]

    def __init__(self, blocked_topics: Optional[list[str]] = None):
        self._blocked_topics = blocked_topics or []
        self._compiled = [
            (re.compile(pattern), category)
            for pattern, category in self.INJECTION_PATTERNS
        ]

    def check(self, prompt: str) -> GuardResult:
        if not prompt or not prompt.strip():
            return GuardResult(allowed=False, reason="Empty prompt not allowed.")

        for compiled, category in self._compiled:
            match = compiled.search(prompt)
            if match:
                logger.warning("Prompt blocked by '%s': matched '%s'", category, match.group())
                return GuardResult(
                    allowed=False,
                    reason=f"Request blocked: potential {category.replace('_', ' ')} detected.",
                    matched_pattern=category,
                )

        if self._blocked_topics:
            for topic in self._blocked_topics:
                if re.search(rf"(?i)\b{re.escape(topic)}\b", prompt):
                    return GuardResult(
                        allowed=False,
                        reason=f"Request blocked: topic '{topic}' is not allowed.",
                        matched_pattern=topic,
                    )

        return GuardResult(allowed=True)


class OutputGuard:
    BLOCKED_PATTERNS: list[tuple[str, str]] = [
        (r"(?i)(ssh-|-----begin\s+(rsa\s+)?private)", "private_key_leak"),
        (r"(?i)(password|passwd|secret|api[_-]?key)\s*[=:]\s*\S{8,}", "credential_leak"),
    ]

    def __init__(self, blocked_topics: Optional[list[str]] = None):
        self._blocked_topics = blocked_topics or []
        self._compiled = [
            (re.compile(pattern), category)
            for pattern, category in self.BLOCKED_PATTERNS
        ]

    def sanitize(self, result: PipelineResult) -> PipelineResult:
        sanitized = result.text

        for compiled, category in self._compiled:
            sanitized = compiled.sub("[REDACTED]", sanitized)

        return PipelineResult(
            text=sanitized,
            generation=result.generation,
            messages=result.messages,
        )

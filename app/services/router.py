import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class RoutedIntent:
    intent: str
    confidence: float
    arguments: dict
    matched_phrase: Optional[str] = None


PATTERNS: list[tuple[str, str, float]] = [
    (r"tell\s+my\s+assistant", "assistant_command", 0.85),
    (r"note\s+to\s+self", "save_note", 0.9),
    (r"remind\s+me", "create_task", 0.9),
    (r"make\s+a\s+task", "create_task", 0.85),
    (r"send\s+this\s+to\s+google\s+chat", "send_google_chat", 0.9),
    (r"log\s+this\s+(business\s+)?idea", "log_business_idea", 0.85),
    (r"remember\s+this", "save_note", 0.8),
    (r"don'?t\s+forget", "create_task", 0.85),
    (r"add\s+to\s+my\s+tasks", "create_task", 0.85),
    (r"turn\s+on\b", "trigger_home_assistant", 0.75),
    (r"turn\s+off\b", "trigger_home_assistant", 0.75),
    (r"home\s+assistant", "trigger_home_assistant", 0.8),
]


def route_text(text: str) -> Optional[RoutedIntent]:
    if not text or not text.strip():
        return None
    lower = text.lower().strip()
    for pattern, intent, confidence in PATTERNS:
        m = re.search(pattern, lower)
        if m:
            remainder = text[m.end() :].strip(" :,-.")
            args: dict = {"text": text, "remainder": remainder}
            if intent == "create_task":
                args["title"] = remainder or text
            elif intent in ("save_note", "log_business_idea"):
                args["body"] = remainder or text
                args["title"] = (remainder or text)[:80]
            elif intent == "send_google_chat":
                args["message"] = remainder or text
            elif intent == "assistant_command":
                args["command"] = remainder or text
            return RoutedIntent(
                intent=intent,
                confidence=confidence,
                arguments=args,
                matched_phrase=m.group(0),
            )
    return None

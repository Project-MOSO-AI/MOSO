"""Rule-based response engine with command detection for tools."""
import re
import random
from typing import Optional


_NAME = "MOSO"
_AUTHOR = "Harsha"


_RESPONSES = {
    r"\bhello\b|\bhi\b|\bhey\b|\bhiya\b": [
        "Hello! I'm {name}. How can I help you?",
        "Hi there! {name} here. What's up?",
        "Hey! Ready to assist.",
    ],
    r"\bhow are you\b|\bhow('s| is) it going\b|\bwhat('s| is) up\b": [
        "I'm doing great! Thanks for asking.",
        "All systems running smoothly. How about you?",
        "Ready and waiting for your command!",
    ],
    r"\bwhat('s| is) your name\b|\bwho are you\b|\btell me about yourself\b": [
        "I'm {name}, a privacy-first local AI assistant. I work entirely on your machine.",
        "My name is {name}. I'm your local AI assistant, built for privacy and speed.",
    ],
    r"\bwho made you\b|\bwho created you\b|\bwho built you\b": [
        "I was created by {author}. He's pretty awesome!",
        "{author} built me as a privacy-first local AI assistant.",
    ],
    r"\bwhat can you do\b|\bhelp\b|\bcapabilities\b": [
        "I can see your screen with OCR, operate your desktop apps, run tools, plan tasks, and chat with you. All locally, no cloud needed.",
        "I can help with desktop automation, screen reading, file management, and general conversation. All processing stays on your machine.",
    ],
    r"\bgoodbye\b|\bbye\b|\bsee you\b|\blater\b": [
        "Goodbye! Talk to you later.",
        "See you! I'll be here when you need me.",
        "Bye! Take care.",
    ],
    r"\bthank(s| you)\b|\bthanks\b|\bappreciate\b": [
        "You're welcome!",
        "Happy to help!",
        "Anytime!",
    ],
    r"\byes\b|\byeah\b|\byep\b|\bsure\b": [
        "Great! What would you like me to do?",
        "Awesome! Tell me what you need.",
        "Okay! I'm listening.",
    ],
    r"\bno\b|\bnah\b|\bnope\b": [
        "Alright. Let me know if you need anything.",
        "Okay. I'm here if you change your mind.",
    ],
}

_STOP_WORDS = {"source", "file", "folder", "directory", "document", "app", "application", "program"}


_CMD_PATTERNS = [
    (r"\bgo to\s+(https?://\S+)", "browser_tool", "open_url",
     lambda m: {"url": m.group(1).strip()}),
    (r"\bopen\s+(https?://\S+)", "browser_tool", "open_url",
     lambda m: {"url": m.group(1).strip()}),
    (r"\b(?:search|find|look up)\s+(?:for\s+)?(.+)", "browser_tool", "search_web",
     lambda m: {"query": m.group(1).strip()}),
    (r"\bclose\s+(.+?)(?:\s+app|\s*)$", "app_tool", "close_application",
     lambda m: {"app_name": m.group(1).strip()}),
    (r"\bkill\s+(.+?)(?:\s+app|\s*)$", "app_tool", "close_application",
     lambda m: {"app_name": m.group(1).strip()}),
    (r"\b(?:open|launch|start)\s+(.+)", "app_tool", "launch_application",
     lambda m: {"app_name": m.group(1).strip()}),
    (r"\blist\s+(?:running\s+)?apps", "app_tool", "list_running_applications", lambda m: {}),
    (r"\bwhat('s| is)\s+running\b", "app_tool", "list_running_applications", lambda m: {}),
    (r"\blist\s+(?:files?|dir|directory|folder)\s*(?:in\s+(.+))?", "file_tool", "list_directory",
     lambda m: {"path": m.group(1).strip() if m.group(1) else "."}),
    (r"\bread\s+(?:file\s+)?(.+)", "file_tool", "read_file",
     lambda m: {"path": m.group(1).strip()}),
    (r"\bcreate\s+(?:a\s+)?(?:folder|directory)\s+(.+)", "file_tool", "create_folder",
     lambda m: {"path": m.group(1).strip()}),
    (r"\bdelete\s+(?:the\s+)?(?:file|folder)\s+(.+)", "file_tool", "delete_file",
     lambda m: {"path": m.group(1).strip()}),
    (r"\bremove\s+(?:the\s+)?(?:file|folder)\s+(.+)", "file_tool", "delete_file",
     lambda m: {"path": m.group(1).strip()}),
    (r"\brun\s+(?:command\s+)?(.+)", "terminal_tool", "run_command",
     lambda m: {"command": m.group(1).strip()}),
]


_DEFAULT_RESPONSES = [
    "That's interesting! Tell me more.",
    "I see. What else is on your mind?",
    "Hmm, I'm not sure what to say about that. I'm still learning!",
    "Got it. Is there something specific you'd like me to help with?",
    "I hear you. As an AI assistant, I'm best at tasks. Want me to do something?",
]


def detect_command(text: str) -> Optional[tuple]:
    text_lower = text.lower().strip()
    for pattern, tool_name, action, param_fn in _CMD_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            params = param_fn(m)
            params["action"] = action
            return (tool_name, params)
    return None


def chat_response(text: str) -> str:
    text_lower = text.lower().strip()
    for pattern, replies in _RESPONSES.items():
        if re.search(pattern, text_lower):
            reply = random.choice(replies)
            return reply.format(name=_NAME, author=_AUTHOR)
    return random.choice(_DEFAULT_RESPONSES)

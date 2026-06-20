"""Rule-based response engine with command detection for tools and module routing."""
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
        "I can see your screen with OCR, operate your desktop apps, run tools, plan tasks, research the web, check your system specs, and chat with you. All locally, no cloud needed.",
        "I can help with desktop automation, screen reading, file management, system intelligence, web research, and general conversation. All processing stays on your machine.",
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
    r"\b(ram|memory|cpu|processor|specs|specifications|hardware|gpu|graphics)\b": [
        "I can check your system specifications. Let me look that up for you...",
        "Let me fetch your hardware information...",
    ],
    r"\b(software|installed|programs|applications)\b": [
        "Let me check what software you have installed.",
        "I can list your installed applications. One moment...",
    ],
    r"\b(news|research|latest|trending|what's new)\b": [
        "Let me research that for you...",
        "I'll look into the latest information on that topic.",
    ],
    r"\b(screen|see|visible|display|ocr|read text)\b": [
        "Let me look at your screen...",
        "I can analyze what's on your screen right now.",
    ],
    r"\b(create|build|make|write)\s+(a\s+)?(python|project|script|app)\b": [
        "I can help set that up! Let me plan the steps...",
        "Let me create that project structure for you...",
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
    (r"\btake\s+a\s+screenshot\b|\bcapture\s+(?:the\s+)?screen\b", "computer_use", "capture_screen",
     lambda m: {}),
    (r"\b(?:what|which)\s+(?:window|app)\s+(?:is\s+)?active\b", "computer_use", "get_active_window",
     lambda m: {}),
    (r"\bmove\s+(?:the\s+)?mouse\s+(?:to\s+)?\(?(\d+)\s*,?\s*(\d+)\)?", "computer_use", "move_mouse",
     lambda m: {"x": int(m.group(1)), "y": int(m.group(2))}),
    (r"\bclick\s+(?:at\s+)?\(?(\d+)\s*,?\s*(\d+)\)?", "computer_use", "click",
     lambda m: {"x": int(m.group(1)), "y": int(m.group(2))}),
    (r"\btype\s+(.+?)(?:\.|$)", "computer_use", "type_text",
     lambda m: {"text": m.group(1).strip()}),
    (r"\bpress\s+(?:the\s+)?(?:key\s+)?(.+?)(?:\.|$)", "computer_use", "press_key",
     lambda m: {"key": m.group(1).strip()}),
    (r"\bscroll\s+(up|down)\b", "computer_use", "scroll",
     lambda m: {"direction": m.group(1)}),
]

_DEFAULT_RESPONSES = [
    "That's interesting! Tell me more.",
    "I see. What else is on your mind?",
    "Hmm, I'm not sure what to say about that. I'm still learning!",
    "Got it. Is there something specific you'd like me to help with?",
    "I hear you. As an AI assistant, I'm best at tasks. Want me to do something?",
    "I understand. Let me know if you need anything — I can check your system, research topics, manage files, automate your desktop, and more.",
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


def detect_intent(text: str) -> str:
    text_lower = text.lower().strip()
    if re.search(r"\b(ram|memory|cpu|processor|specs?|hardware|gpu|graphics|motherboard|os |operating system)\b", text_lower):
        return "system_hardware"
    if re.search(r"\b(software|installed|programs?|applications?|running)\b", text_lower):
        return "system_software"
    if re.search(r"\b(news|research|latest|trending|what('s| is) new|compare|vs |versus)\b", text_lower):
        return "research"
    if re.search(r"\b(screen|see |visible|display|ocr|read text|what('s| is) on)\b", text_lower):
        return "vision"
    if re.search(r"\b(remember|recall|what did|what was|earlier|yesterday|before)\b", text_lower) and re.search(r"\b(i |me|we|you|said|discuss|talk)\b", text_lower):
        return "memory_retrieval"
    if re.search(r"\b(create|build|make|write|set up)\s+(a\s+)?(python|project|script|virtual env|folder)\b", text_lower):
        return "agent"
    if re.search(r"\b(click|screenshot|capture|mouse|type |press |scroll|focus)\b", text_lower):
        return "computer_use"
    if re.search(r"\b(diagnos|health|issue|problem|check|scan|optimize)\b", text_lower):
        return "system_diagnostics"
    return "general"


def chat_response(text: str) -> str:
    text_lower = text.lower().strip()
    for pattern, replies in _RESPONSES.items():
        if re.search(pattern, text_lower):
            reply = random.choice(replies)
            return reply.format(name=_NAME, author=_AUTHOR)
    return random.choice(_DEFAULT_RESPONSES)

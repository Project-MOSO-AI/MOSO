"""Simple rule-based response engine for when no LLM model is loaded."""
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
        "Great! What would you like to do?",
        "Awesome! Tell me more.",
        "Okay! I'm listening.",
    ],
    r"\bno\b|\bnah\b|\bnope\b": [
        "Alright. Let me know if you need anything.",
        "Okay. I'm here if you change your mind.",
    ],
    r"\bweather\b": [
        "I don't have internet access for weather data. Check your favorite weather app!",
    ],
    r"\btime\b": [
        "I don't have a clock right now, but check your system tray!",
    ],
}


_DEFAULT_RESPONSES = [
    "That's interesting! Tell me more.",
    "I see. What else is on your mind?",
    "Hmm, I'm not sure what to say about that. I'm still learning!",
    "Got it. Is there something specific you'd like me to help with?",
    "I hear you. As an AI assistant, I'm best at tasks. Want me to do something?",
]


def generate_response(text: str) -> str:
    text_lower = text.lower().strip()

    for pattern, replies in _RESPONSES.items():
        if re.search(pattern, text_lower):
            reply = random.choice(replies)
            return reply.format(name=_NAME, author=_AUTHOR)

    return random.choice(_DEFAULT_RESPONSES)

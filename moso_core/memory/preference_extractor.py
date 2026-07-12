import logging
from typing import Optional

from moso_core.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

class PreferenceExtractor:
    def __init__(self, memory_manager: MemoryManager, llm=None):
        self._memory = memory_manager
        self._llm = llm

    def extract_from_chat(self, user_input: str, assistant_response: str) -> Optional[bool]:
        """
        Extracts preferences in the background after a chat turn.
        Returns True if a preference was extracted and saved, False/None otherwise.
        """
        if not self._llm:
            return False

        prompt = f"""
Analyze the following conversation turn between a User and MOSO.
Did the user explicitly or implicitly state a preference, like, dislike, or personal fact?
(e.g., "I prefer dark mode", "I love lofi music", "Don't use Edge", "My name is Harsha")

User: {user_input}
MOSO: {assistant_response}

If there is a preference, output ONLY a JSON object with:
{{
  "category": "music | app | ui | personal | other",
  "value": "the extracted preference",
  "confidence": 0.0 to 1.0
}}
If there is no preference, output the exact word "NONE".
"""
        try:
            resp = self._llm.chat(prompt)
            if "NONE" in resp.strip().upper():
                return False
                
            import json
            import re
            json_match = re.search(r'\{.*\}', resp, re.DOTALL)
            if json_match:
                pref = json.loads(json_match.group(0))
                self._memory.store_preference(
                    category=pref.get("category", "other"),
                    value=pref.get("value", ""),
                    confidence=pref.get("confidence", 0.8)
                )
                logger.info(f"Extracted and saved preference: {pref.get('value')} ({pref.get('category')})")
                return True
        except Exception as e:
            logger.error(f"Preference extraction failed: {e}")
            return False
            
        return False

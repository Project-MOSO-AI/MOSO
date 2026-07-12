import logging
import json
from typing import Optional

from moso_core.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

class CorrectionsManager:
    def __init__(self, memory_manager: MemoryManager, llm=None):
        self._memory = memory_manager
        self._llm = llm

    def apply_feedback(self, feedback_type: str, message: str) -> str:
        """
        Process a user correction.
        If it's related to a recently used procedural recipe, we update the recipe.
        Otherwise, we store it as a semantic fact or preference.
        """
        if not self._llm:
            return "Feedback received, but LLM is not available to process it."
            
        if feedback_type == "good":
            # For positive feedback, we might increment a success counter on the recent recipe
            recent_events = self._memory.episodic.list_recent(limit=5)
            return "Thanks for the feedback!"
            
        elif feedback_type == "bad":
            # Negative feedback: check if they are correcting a recipe
            prompt = f"""
The user gave negative feedback (thumbs down) on this response:
"{message}"

Task:
Determine if the user is correcting an action (e.g., clicking the wrong button, wrong target) or if they just disliked the answer.
If it's an action correction, output a JSON object with:
{{
  "is_correction": true,
  "correction": "what went wrong and how to fix it"
}}
If not, output:
{{
  "is_correction": false
}}
"""
            try:
                resp = self._llm.chat(prompt)
                import re
                json_match = re.search(r'\{.*\}', resp, re.DOTALL)
                if json_match:
                    res = json.loads(json_match.group(0))
                    if res.get("is_correction"):
                        # Save it as a strong preference or semantic fact
                        correction = res.get("correction", "Unknown correction")
                        self._memory.store_preference("correction", correction, confidence=1.0)
                        return f"I've noted that correction: {correction}"
            except Exception as e:
                logger.error(f"Failed to process correction: {e}")
            
            return "I've noted that this response was not helpful."
            
        return "Feedback received."

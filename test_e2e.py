import logging
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from moso_core.computer_use.agent import ComputerUseAgent
from moso_core.computer_use.automation import AutomationEngine

engine = AutomationEngine()
agent = ComputerUseAgent(engine)

print("=== Step 1: Open Chrome ===")
r = agent.execute("open chrome")
print(f"Result: {r}")
print()

print("=== Step 2: Search YouTube ===")
r = agent.execute("search youtube")
print(f"Result: {r}")
print()

print("=== Step 3: Read screen (what loaded?) ===")
screen = agent.screen_reader.read_screen()
text = screen.get("full_text", "")
print(f"Screen text ({len(text)} chars):")
print(text[:400])

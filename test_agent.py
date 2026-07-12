from moso_core.computer_use.agent import ComputerUseAgent, ScreenReader
from moso_core.computer_use.automation import AutomationEngine

engine = AutomationEngine()
agent = ComputerUseAgent(engine)

screen_data = agent.screen_reader.read_screen()
elements = screen_data.get("elements", [])
print(f"Found {len(elements)} text elements")
for el in elements[:15]:
    t = el["text"]
    x, y = el["x"], el["y"]
    c = el["confidence"]
    print(f"  {t:30s} at ({x:4d}, {y:4d}) conf={c:.0f}")
print()
ft = screen_data.get("full_text", "")
print(f"Full text ({len(ft)} chars):")
print(ft[:300])

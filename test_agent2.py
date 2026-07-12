from moso_core.computer_use.agent import ComputerUseAgent
from moso_core.computer_use.automation import AutomationEngine

engine = AutomationEngine()
agent = ComputerUseAgent(engine)

# Test 1: Read screen
print("=== Test 1: Read Screen ===")
result = agent.execute("what is on my screen")
print(result)
print()

# Test 2: Find specific text
print("=== Test 2: Find 'Pixel' on screen ===")
screen = agent.screen_reader.read_screen()
el = agent.screen_reader.find_text("Pixel", screen)
if el:
    print(f"Found: '{el['text']}' at ({el['x']}, {el['y']})")
else:
    print("Not found")
print()

# Test 3: Plan a multi-step task
print("=== Test 3: Plan 'open chrome and search youtube' ===")
from moso_core.computer_use.agent import TaskPlanner
planner = TaskPlanner()
steps = planner.plan("open chrome and search youtube")
for i, s in enumerate(steps, 1):
    print(f"  {i}. {s.action}: {s.params}")
print()

# Test 4: Minimize window
print("=== Test 4: Minimize window ===")
result = agent.execute("minimize window")
print(result)

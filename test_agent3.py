from moso_core.computer_use.agent import ComputerUseAgent, TaskPlanner
from moso_core.computer_use.automation import AutomationEngine

engine = AutomationEngine()
agent = ComputerUseAgent(engine)
planner = TaskPlanner()

# Test 1: Permission fix
print("=== Test 1: Minimize window (permission fix) ===")
result = agent.execute("minimize window")
print(result)
print()

# Test 2: Compound command splitting
print("=== Test 2: Plan compound command ===")
steps = planner.plan("open chrome and search youtube")
for i, s in enumerate(steps, 1):
    print(f"  {i}. {s.action}: {s.params}")
print()

# Test 3: find_text matching
print("=== Test 3: Find text on screen ===")
screen = agent.screen_reader.read_screen()
elements = screen.get("elements", [])
print(f"Screen has {len(elements)} elements")

# Show some actual elements to search for
for el in elements[:5]:
    print(f"  element: '{el['text']}' at ({el['x']}, {el['y']})")

if elements:
    # Try finding first real element
    target = elements[3]["text"] if len(elements) > 3 else elements[0]["text"]
    found = agent.screen_reader.find_text(target, screen)
    if found:
        print(f"  Found '{found['text']}' at ({found['x']}, {found['y']})")
    else:
        print(f"  NOT found: '{target}'")
print()

# Test 4: Read screen
print("=== Test 4: Read screen ===")
result = agent.execute("what is on my screen")
print(result[:500])

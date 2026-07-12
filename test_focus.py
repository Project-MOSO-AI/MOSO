import pygetwindow as gw
import time

from moso_core.tools.app_tool import AppTool
AppTool().launch_application("chrome")
time.sleep(3)

wins = gw.getWindowsWithTitle("chrome")
print(f"getWindowsWithTitle returns {len(wins)} windows:")
for w in wins:
    print(f"  title={w.title!r} active={w.isActive}")

from moso_core.computer_use.windows import WindowManager
wm = WindowManager()
r = wm.focus_window("chrome")
print(f"focus result: {r.success}")
time.sleep(1)
active = gw.getActiveWindow()
print(f"After focus: {active.title if active else None}")
for w in gw.getWindowsWithTitle("chrome"):
    if "opera" not in w.title.lower():
        print(f"Chrome isActive={w.isActive}")

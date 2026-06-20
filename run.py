"""
MOSO AI Launcher

Usage:
  python run.py         - Launch Aura UI desktop orb (click or press Space to talk)
  python run.py demo    - Run module demos (memory, resources, tools, agents, CU, vision)
  python run.py test    - Run all 130 tests
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "MOSO"))

if len(sys.argv) > 1 and sys.argv[1].lower() == "demo":
    os.chdir(os.path.join(os.path.dirname(__file__), "MOSO"))
    exec(open("scripts/demo_all.py").read())
elif len(sys.argv) > 1 and sys.argv[1].lower() == "test":
    import subprocess
    sys.exit(subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd=os.path.join(os.path.dirname(__file__), "MOSO")).returncode)
else:
    from moso_ui.main import main
    main()

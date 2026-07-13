<div align="center">

<!-- Animated Matrix SVG Logo -->
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120">
  <defs>
    <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00ff41;stop-opacity:1">
        <animate attributeName="stop-color" values="#00ff41;#00cc00;#00ff41" dur="3s" repeatCount="indefinite"/>
      </stop>
      <stop offset="100%" style="stop-color:#00cc00;stop-opacity:1">
        <animate attributeName="stop-color" values="#00cc00;#00ff41;#00cc00" dur="3s" repeatCount="indefinite"/>
      </stop>
    </linearGradient>
    <filter id="glowFilter">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="glowStrong">
      <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Matrix rain background -->
  <text x="50" y="20" fill="#00ff41" opacity="0.08" font-family="monospace" font-size="8">
    <tspan x="10">01001101 01001111 01010011 01001111</tspan>
    <tspan x="10" y="30">01001101 01000101 01001101 01001111</tspan>
    <tspan x="10" y="40">01010010 01011001 00100000 01000001</tspan>
    <tspan x="10" y="50">01001001 00100000 01010000 01010010</tspan>
    <tspan x="10" y="60">01001001 01010110 01000001 01000011</tspan>
    <tspan x="10" y="70">01011001 00100000 01000110 01001001</tspan>
    <tspan x="10" y="80">01010010 01010011 01010100 00001010</tspan>
  </text>

  <!-- MOSO AI with glow -->
  <text x="200" y="55" fill="url(#glow)" filter="url(#glowStrong)" font-family="monospace" font-size="48" font-weight="bold" text-anchor="middle" letter-spacing="4">
    MOSO AI
    <animate attributeName="opacity" values="1;0.85;1" dur="2s" repeatCount="indefinite"/>
  </text>

  <!-- Subtitle with scan animation -->
  <text x="200" y="78" fill="#00ff41" font-family="monospace" font-size="13" text-anchor="middle" letter-spacing="3" opacity="0.8">
    PRIVACY-FIRST ADAPTIVE INTELLIGENCE
    <animate attributeName="letter-spacing" values="3;5;3" dur="4s" repeatCount="indefinite"/>
  </text>

  <!-- Scanning line -->
  <rect x="50" y="0" width="300" height="2" fill="#00ff41" opacity="0.6" filter="url(#glow)">
    <animate attributeName="y" values="0;118;0" dur="4s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.6;0;0.6" dur="4s" repeatCount="indefinite"/>
  </rect>

  <!-- Glowing corner brackets -->
  <path d="M40 20 L50 20 L50 10" stroke="#00ff41" stroke-width="2" fill="none" opacity="0.8" filter="url(#glow)">
    <animate attributeName="opacity" values="0.8;0.4;0.8" dur="2.5s" repeatCount="indefinite"/>
  </path>
  <path d="M360 20 L350 20 L350 10" stroke="#00ff41" stroke-width="2" fill="none" opacity="0.8" filter="url(#glow)">
    <animate attributeName="opacity" values="0.8;0.4;0.8" dur="2.5s" repeatCount="indefinite"/>
  </path>
  <path d="M40 100 L50 100 L50 110" stroke="#00ff41" stroke-width="2" fill="none" opacity="0.8" filter="url(#glow)">
    <animate attributeName="opacity" values="0.4;0.8;0.4" dur="2.5s" repeatCount="indefinite"/>
  </path>
  <path d="M360 100 L350 100 L350 110" stroke="#00ff41" stroke-width="2" fill="none" opacity="0.8" filter="url(#glow)">
    <animate attributeName="opacity" values="0.4;0.8;0.4" dur="2.5s" repeatCount="indefinite"/>
  </path>

  <!-- Pulsing dots -->
  <circle cx="100" cy="105" r="2" fill="#00ff41" filter="url(#glow)">
    <animate attributeName="r" values="2;4;2" dur="1.5s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.3;1" dur="1.5s" repeatCount="indefinite"/>
  </circle>
  <circle cx="130" cy="105" r="2" fill="#00ff41" filter="url(#glow)">
    <animate attributeName="r" values="2;4;2" dur="1.5s" begin="0.3s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.3;1" dur="1.5s" begin="0.3s" repeatCount="indefinite"/>
  </circle>
  <circle cx="160" cy="105" r="2" fill="#00ff41" filter="url(#glow)">
    <animate attributeName="r" values="2;4;2" dur="1.5s" begin="0.6s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.3;1" dur="1.5s" begin="0.6s" repeatCount="indefinite"/>
  </circle>
</svg>

<br/>

<!-- Status Badges -->
<a href="#"><img src="https://img.shields.io/badge/Status-Development-00ff41?style=flat-square&labelColor=0a0a0a" alt="Status"/></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-Source_Available-00ff41?style=flat-square&labelColor=0a0a0a" alt="License"/></a>
<a href="#"><img src="https://img.shields.io/badge/Version-0.2.0--dev-ffffff?style=flat-square&labelColor=0a0a0a" alt="Version"/></a>

<br/>

<blockquote style="border-left: 4px solid #00ff41; background: rgba(0, 255, 65, 0.03); padding: 16px; border-radius: 4px;">
  <p align="center" style="margin: 0; color: #888;">
    Viewing access does not grant usage rights.
    <a href="LICENSE" style="color: #00ff41;">MOSO Source Available License</a>.
    Written permission required for use, modification, or distribution.
  </p>
</blockquote>

</div>

---

## What is MOSO?

**MOSO** is a **privacy-first, local-first AI assistant** that runs entirely on your device. It sees your screen, understands your system, and acts on your behalf — all without sending data to the cloud.

```
User Goal → Brain (plan) → Muscles (act) → Eyes (verify) → Memory (learn)
```

---

## Architecture

```
                    ┌──────────┐
                    │  BRAIN   │  Goal understanding, planning, reasoning
                    └────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
       ┌──────┐    ┌──────────┐    ┌─────────┐
       │ EYES │    │  MEMORY  │    │ MUSCLES │
       │      │    │          │    │         │
       │ OCR  │    │ Episodic │    │ Mouse   │
       │ Screenshot│ │ Semantic│    │ Keyboard│
       │ Window│    │ Procedural   │ Browser │
       │ Detect│    │ Vector   │    │ Terminal│
       └──────┘    └──────────┘    │ Files   │
                                   └─────────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                    ┌────▼─────┐
                    │ LEARNER  │  Skills from experience
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  SAFETY  │  Risk scoring, permissions
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │    UI    │  Aura orb + chat
                    └──────────┘
```

**Seven organs. No app-specific code. No cloud dependency.**

> **Full architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete organ interfaces, database schemas, event flow, and migration plan.

| Module | What It Does | Key Files |
|--------|-------------|-----------|
| **Brain** | Plans, reasons, reflects | `agents/` (planner, executor, verifier) |
| **Eyes** | Sees your screen | `vision/` (OCR, screenshots, window detection) |
| **Muscles** | Acts on your system | `tools/` + `computer_use/` (mouse, keyboard, files, terminal) |
| **Memory** | Remembers everything | `memory/` (episodic, semantic, procedural, vector search) |
| **Learning** | Self-improvement engine | `learning/` (experience, reflection, skill builder, generalization, optimizer, curriculum, evaluation) |
| **Safety** | Blocks dangerous actions | `risk/` (permissions, privacy, risk scoring) |
| **UI** | Desktop orb + conversation | `moso_ui/` (PySide6 floating orb) |

---

## Quick Start

### Step 1: Install Python 3.12+

```bash
# Check your version
python --version
```

### Step 2: Clone and install

```bash
git clone https://github.com/Project-MOSO-AI/MOSO.git
cd MOSO

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r moso_core/requirements.txt
```

### Step 3: Download a model

```bash
# Lightweight (~2.3 GB)
python scripts/download_model.py phi3-mini

# Or larger (~5.2 GB, better quality)
python scripts/download_model.py qwen3-8b
```

### Step 4: Run MOSO

```bash
# Launch desktop UI (Aura orb)
python run.py

# Or run module demos
python run.py demo

# Or run tests
python run.py test
```

---

## Step-by-Step Usage

### 1. Basic Chat

```python
from moso_core.inference.base import InferenceConfig
from moso_core.orchestration.orchestrator import Orchestrator

config = InferenceConfig(model_path="models/phi3-mini-3.8b-q4_k_m.gguf")
orchestrator = Orchestrator(config)

result = orchestrator.process("Hello, what can you do?")
print(result.text)
```

### 2. Enable Memory

```python
orchestrator.enable_memory()

# MOSO remembers across sessions
orchestrator.process("My name is Alice")
orchestrator.process("What's my name?")  # → "Alice"
```

### 3. Use Tools

```python
orchestrator.enable_tools()
orchestrator.enable_identity()

from moso_core.tools.models import ToolRequest

# Launch an app
req = ToolRequest(
    tool_name="app_tool",
    parameters={"action": "launch_application", "app_name": "code"},
)
result = orchestrator.tools.execute_tool(req, identity=orchestrator.identity_verifier)

# Read a file
req = ToolRequest(
    tool_name="file_tool",
    parameters={"action": "read_file", "path": "notes.txt"},
)
result = orchestrator.tools.execute_tool(req)
```

### 4. Automate Tasks

```python
orchestrator.enable_agents()

summary = orchestrator.agents.plan_and_execute(
    "create a python project named my_app",
    requester="owner",
)
print(summary.overall_status)  # GoalStatus.COMPLETED
```

### 5. Control Your Desktop

```python
orchestrator.enable_computer_use()

# Take a screenshot
result = orchestrator.computer_use.execute_action({"action": "capture_screen"})

# Type text
result = orchestrator.computer_use.execute_action(
    {"action": "type_text", "text": "Hello from MOSO"}
)

# Execute a sequence
results = orchestrator.computer_use.execute_sequence([
    {"action": "move_to", "x": 500, "y": 200},
    {"action": "click"},
    {"action": "type_text", "text": "MOSO AI"},
])
```

### 6. See Your Screen

```python
orchestrator.enable_vision()

ctx = orchestrator.vision.build_context()
print(f"Active window: {ctx.active_window}")
print(f"Text on screen: {ctx.text_content[:200]}")
```

### 7. Ask About Your System

```python
orchestrator.enable_system_intelligence()

print(orchestrator.system_intelligence.get_hardware_summary())
print(orchestrator.system_intelligence.explain("what is RAM"))
```

### 8. Research the Web

```python
orchestrator.enable_realtime()

response = orchestrator.research("latest Python 3.13 features")
print(response.formatted_report)
```

### 9. Launch Desktop UI

```bash
# Install PySide6 first
pip install PySide6

# Launch the Aura orb
python -m moso_ui.main
```

The floating orb gives you:
- **Click** to open chat
- **Drag** to reposition
- **System tray** for settings

---

## Enable Everything at Once

```python
config = InferenceConfig(model_path="models/qwen3-8b-q4_k_m.gguf")
orchestrator = Orchestrator(config)
orchestrator.enable_all(model_path="models/qwen3-8b-q4_k_m.gguf")

# Now MOSO can: chat, remember, see, act, plan, research, and understand your system
```

---

## Project Structure

```
MOSO/
├── moso_core/                # Core AI engine
│   ├── agents/               # Brain — planning, execution, verification
│   ├── computer_use/         # Muscles — mouse, keyboard, screen, windows
│   ├── desktop/              # Desktop agent — perceive→reason→act→verify loop
│   ├── identity/             # Owner verification (voice, behavior, device)
│   ├── inference/            # Model backends (llama.cpp, ONNX Runtime)
│   ├── llm/                  # LLM integration (local, OpenAI, Anthropic, Ollama)
│   ├── learner/              # Learning engine — skills from experience
│   ├── memory/               # Memory — episodic, semantic, procedural, vector
│   ├── orchestration/        # Central hub — connects all modules
│   ├── realtime/             # Web research — fetch, verify, analyze, summarize
│   ├── resources/            # System monitoring — CPU, RAM, storage, network
│   ├── risk/                 # Safety — risk scoring, privacy, permissions
│   ├── tools/                # Tools — file, app, browser, terminal
│   ├── vision/               # Eyes — OCR, screenshots, window detection
│   └── voice/                # Voice pipeline — STT, TTS, speaker verify
├── moso_ui/                  # Desktop UI — Aura floating orb
├── backend/                  # FastAPI backend
├── tests/                    # Test suite (249 tests)
├── scripts/                  # Utility scripts
├── models/                   # Local GGUF model storage
├── run.py                    # Entry point
└── llms.txt                  # LLM context summary
```

---

## Key Concepts

### Experience → Skill Loop

Every action MOSO takes is recorded:

```
Screen Before → Action → Screen After → Success/Fail
```

When the same sequence succeeds multiple times, MOSO extracts a **skill**:

```
"Play {song_name} on Spotify"
Variables: song_name
Success rate: 95%
```

Skills are stored in procedural memory and reused for future tasks.

### Risk Scoring

Before any action, MOSO calculates a risk score:

| Score | Level | What Happens |
|-------|-------|-------------|
| < 0.2 | LOW | Allowed |
| 0.2–0.5 | MEDIUM | Allowed with review |
| 0.5–0.8 | HIGH | Blocked |
| ≥ 0.8 | CRITICAL | Blocked |

### Identity Levels

| Level | Score | Permissions |
|-------|-------|-------------|
| Owner | 95+ | Full access |
| Likely | 80–94 | Standard access |
| Guest | 60–79 | Limited |
| Unknown | < 60 | Read-only |

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.12 | Huge AI ecosystem |
| Inference | llama.cpp | Best local inference |
| Memory | SQLite + WAL | Plenty for local AI |
| Vision | pytesseract + mss | Stable OCR |
| Automation | pyautogui + pygetwindow | Desktop control |
| UI | PySide6 | Native desktop |
| API | FastAPI | Fast, simple |
| Config | Pydantic | Clean settings |
| Testing | pytest | Standard |

---

## Docker

```bash
# Pull the image
docker pull ghcr.io/project-moso-ai/moso:latest

# Run it
docker run -d -p 8000:8000 --name moso ghcr.io/project-moso-ai/moso:latest

# Verify
curl http://localhost:8000/health

# Full stack with Redis
docker compose up -d
```

---

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Voice Pipeline | ✅ |
| 2 | Identity Engine | ✅ |
| 3 | Memory Engine | ✅ |
| 4 | Resource Manager | ✅ |
| 5 | Tool Engine | ✅ |
| 6 | Agent System | ✅ |
| 7 | Computer Use | ✅ |
| 8 | Screen Vision | ✅ |
| 9 | LLM Integration | ✅ |
| 10 | Aura UI | ✅ |
| 11 | Risk & Privacy | ✅ |
| 12 | Real-Time Intelligence | ✅ |
| 13 | Knowledge Graph | ✅ |
| 14 | Learning Engine (7 sub-engines) | 🔄 In Progress |
| 15 | Architecture v2 (7-organ redesign) | 📋 Planned |

---

## Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_risk.py -v
```

---

## License

**MOSO Source Available License v1.0**

Copyright (c) 2024-2026 MOSO AI

Viewing access does not grant usage rights. Written permission required for use, modification, or distribution.

---

<p align="center">
  <strong>MOSO AI</strong> — Privacy-First Adaptive Intelligence<br/>
  <a href="LICENSE">License</a> · <a href="https://github.com/Project-MOSO-AI/MOSO">GitHub</a>
</p>

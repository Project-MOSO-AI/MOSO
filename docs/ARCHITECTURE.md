# MOSO Architecture v2.0

## Design Philosophy

MOSO is not a chatbot with plugins. It is a self-improving operating system that learns from every interaction. The architecture is built around seven organs, each with a single responsibility. Learning is not a module — it is the circulatory system that connects everything.

**Three axioms:**
1. **Experience** is raw history. What happened, when, and what changed.
2. **Skills** are reusable procedures. How to do something, with variables.
3. **Knowledge** is factual understanding. What is true about the world.

These three are never mixed. They live in separate stores, are produced by separate engines, and are consumed by separate readers.

---

## Organ Map

```
                         ┌─────────────────────┐
                         │        BRAIN         │
                         │  Plan · Reason ·     │
                         │  Reflect · Decide    │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
     ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
     │      EYES      │   │     MEMORY     │   │    MUSCLES     │
     │                │   │                │   │                │
     │  Screen OCR    │   │  Experience    │   │  Mouse         │
     │  UI Detection  │   │  Skills        │   │  Keyboard      │
     │  Window State  │   │  Knowledge     │   │  Browser       │
     │  System Watch  │   │  Preferences   │   │  Shell         │
     │  Error Logs    │   │  Vector Search │   │  Filesystem    │
     └────────────────┘   └────────────────┘   └────────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
          ┌─────────────────┐             ┌─────────────────┐
          │     LEARNING    │             │     SAFETY      │
          │                 │             │                 │
          │  Experience     │             │  Permissions    │
          │  Reflection     │             │  Risk Scoring   │
          │  Skill Builder  │             │  Privacy        │
          │  Generalization │             │  Identity       │
          │  Optimizer      │             │  Confirmation   │
          │  Curriculum     │             │                 │
          │  Evaluation     │             │                 │
          └─────────────────┘             └─────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                              ┌─────▼─────┐
                              │     UI    │
                              │           │
                              │  Orb      │
                              │  Chat     │
                              │  Voice    │
                              │  Status   │
                              └───────────┘
```

---

## The Core Loop

Every task follows this sequence. No exceptions.

```
User Goal / System Event
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                    1. OBSERVE                              │
│  Eyes capture screen state, window, UI elements, errors   │
│  Memory retrieves relevant past experiences               │
│  System resources checked                                 │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                    2. REASON                               │
│  Brain decomposes goal into steps                         │
│  Selects existing skill OR plans new sequence             │
│  Risk engine scores proposed actions                      │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                    3. ACT                                  │
│  Muscles execute: mouse, keyboard, browser, shell, files  │
│  Each action logged with before/after state               │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                    4. VERIFY                               │
│  Brain checks: did the action achieve the expected result?│
│  Eyes re-observe: what changed on screen?                 │
│  Comparator: expected state vs actual state               │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                    5. REFLECT                              │
│  Learning.Reflection asks: why did it succeed or fail?    │
│  Identifies root cause, not just symptom                  │
│  Updates failure patterns for future avoidance            │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                    6. LEARN                                │
│  Learning.SkillBuilder: extract reusable procedure        │
│  Learning.Generalization: replace constants with vars     │
│  Learning.Curriculum: prioritize next things to learn     │
│  Learning.Evaluation: test skill quality                  │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                    7. IMPROVE                              │
│  Learning.Optimizer: tune existing skills                 │
│  Memory stores: experience + skill + knowledge            │
│  Brain updates planning heuristics                        │
│  Next execution starts from a better baseline             │
└───────────────────────────────────────────────────────────┘
```

---

## Organ 1: BRAIN

**Responsibility:** Goal understanding, planning, reasoning, reflection, decision making.

The Brain never touches hardware. It receives observations, produces plans, and evaluates outcomes.

### Interface

```python
class Brain:
    """Central reasoning engine. Orchestrates the core loop."""

    def __init__(
        self,
        eyes: "Eyes",
        muscles: "Muscles",
        memory: "Memory",
        learning: "Learning",
        safety: "Safety",
    ): ...

    # --- Planning ---
    def create_plan(self, goal: str, context: Observation) -> Plan: ...
    def decompose(self, goal: str, available_skills: list[Skill]) -> list[PlanStep]: ...
    def select_skill(self, goal: str, candidates: list[Skill]) -> Skill | None: ...

    # --- Execution ---
    def execute(self, plan: Plan) -> ExecutionResult: ...
    def step(self, step: PlanStep) -> StepResult: ...

    # --- Reflection ---
    def reflect(self, result: ExecutionResult, expected: ExpectedOutcome) -> Reflection: ...
    def diagnose_failure(self, step: PlanStep, error: str) -> FailureDiagnosis: ...
    def should_retry(self, diagnosis: FailureDiagnosis, attempt: int) -> bool: ...

    # --- Decision ---
    def decide_action(self, observation: Observation, goal: Goal) -> Action: ...
    def assess_progress(self, plan: Plan, current: StepResult) -> ProgressAssessment: ...
```

### Models

```python
@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
    context: Observation
    skill_id: str | None          # Reused skill, if any
    created_at: datetime
    estimated_steps: int

@dataclass
class PlanStep:
    action: str                   # tool name or skill name
    parameters: dict
    expected_outcome: ExpectedOutcome
    risk_level: RiskLevel
    depends_on: list[int]         # Step indices
    order: int

@dataclass
class ExecutionResult:
    plan: Plan
    step_results: list[StepResult]
    overall_status: GoalStatus    # completed | failed | partial
    total_time_ms: int

@dataclass
class StepResult:
    step: PlanStep
    success: bool
    actual_outcome: ActualOutcome
    error: str | None
    execution_time_ms: int
    screen_before: str            # Screenshot hash
    screen_after: str             # Screenshot hash

@dataclass
class Reflection:
    result: ExecutionResult
    root_cause: str               # Why it succeeded or failed
    what_worked: list[str]
    what_failed: list[str]
    improvement_suggestion: str
    should_create_skill: bool
    failure_pattern: str | None   # Recurring failure type
```

### Integration Points

| Connects To | Direction | Data |
|-------------|-----------|------|
| Eyes | Read | `Observation` (screen state, context) |
| Memory | Read | `Skill`, `Experience`, `Knowledge` |
| Muscles | Write | `Action` (tool calls) |
| Safety | Read | `RiskReport` (pre-execution check) |
| Learning | Read/Write | `Reflection`, `SkillCandidate` |
| UI | Write | Status updates, progress |

---

## Organ 2: EYES

**Responsibility:** Observe only. Capture screen state, detect UI elements, read text, monitor system. Never perform actions.

### Interface

```python
class Eyes:
    """Observation engine. Reads the world, never modifies it."""

    def observe(self) -> Observation: ...
    def capture_screen(self) -> ScreenCapture: ...
    def detect_ui_elements(self) -> list[UIElement]: ...
    def read_text(self) -> ScreenText: ...
    def get_window_state(self) -> WindowState: ...
    def get_system_state(self) -> SystemState: ...
    def watch_errors(self) -> list[SystemError]: ...
    def diff(self, before: Observation, after: Observation) -> StateDiff: ...
```

### Models

```python
@dataclass
class Observation:
    timestamp: datetime
    screen: ScreenCapture
    ui_elements: list[UIElement]
    text: ScreenText
    window: WindowState
    system: SystemState
    errors: list[SystemError]
    screenshot_hash: str          # For dedup / diff

@dataclass
class UIElement:
    text: str
    role: str                     # button, textbox, link, menu, etc.
    x: int
    y: int
    width: int
    height: int
    focused: bool
    enabled: bool
    confidence: float             # Detection confidence

@dataclass
class ScreenText:
    full_text: str                # All visible text
    regions: list[TextRegion]     # Text with bounding boxes

@dataclass
class TextRegion:
    text: str
    confidence: float
    bbox: BoundingBox

@dataclass
class WindowState:
    active_window: str
    all_windows: list[str]
    resolution: tuple[int, int]

@dataclass
class SystemState:
    cpu_percent: float
    ram_percent: float
    battery_percent: float | None
    network_connected: bool

@dataclass
class StateDiff:
    text_changed: bool
    elements_changed: bool
    window_changed: bool
    new_errors: list[SystemError]
    changed_regions: list[TextRegion]
```

### Module Mapping

| Current Module | Maps To |
|---------------|---------|
| `moso_core/vision/` | `Eyes` (OCR, screenshot, context) |
| `moso_core/desktop/perception.py` | `Eyes` (UI element detection) |
| `moso_core/system_intelligence/` | `Eyes` (system state monitoring) |
| `moso_core/resources/` | `Eyes` (resource monitoring) |

---

## Organ 3: MUSCLES

**Responsibility:** Execute only. Mouse, keyboard, browser, shell, filesystem. Never make decisions.

### Interface

```python
class Muscles:
    """Action engine. Executes commands, never decides them."""

    def execute(self, action: Action) -> ActionResult: ...
    def execute_sequence(self, actions: list[Action]) -> list[ActionResult]: ...
    def mouse(self, action: MouseAction) -> ActionResult: ...
    def keyboard(self, action: KeyboardAction) -> ActionResult: ...
    def browser(self, action: BrowserAction) -> ActionResult: ...
    def shell(self, command: str, timeout: int = 30) -> ActionResult: ...
    def filesystem(self, action: FileAction) -> ActionResult: ...
    def clipboard(self, action: ClipboardAction) -> ActionResult: ...
```

### Models

```python
@dataclass
class Action:
    type: ActionType              # mouse | keyboard | browser | shell | filesystem | clipboard
    command: str                  # Specific action name
    parameters: dict
    timeout_ms: int = 30000
    dry_run: bool = False

@dataclass
class ActionResult:
    success: bool
    action: Action
    output: Any                   # Command output, file content, etc.
    error: str | None
    execution_time_ms: int

class ActionType(str, Enum):
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    BROWSER = "browser"
    SHELL = "shell"
    FILESYSTEM = "filesystem"
    CLIPBOARD = "clipboard"
```

### Module Mapping

| Current Module | Maps To |
|---------------|---------|
| `moso_core/tools/` | `Muscles` (file, app, browser, terminal) |
| `moso_core/computer_use/` | `Muscles` (mouse, keyboard, screen, windows) |
| `moso_core/desktop/action_executor.py` | `Muscles` (action dispatch) |

---

## Organ 4: MEMORY

**Responsibility:** Store and retrieve three distinct types of information. Never confuse them.

### The Three Stores

```
┌─────────────────────────────────────────────────────────────┐
│                         MEMORY                               │
│                                                              │
│  ┌──────────────────┐  What happened                        │
│  │   EXPERIENCE     │  Raw history of actions + outcomes    │
│  │                  │  "I clicked button X, it worked"      │
│  │  - Events        │                                        │
│  │  - Actions       │                                        │
│  │  - Outcomes      │                                        │
│  │  - Timestamps    │                                        │
│  └──────────────────┘                                        │
│                                                              │
│  ┌──────────────────┐  How to do things                     │
│  │   SKILLS         │  Reusable procedures with variables   │
│  │                  │  "To play song: search, select, play" │
│  │  - Steps         │                                        │
│  │  - Variables     │                                        │
│  │  - Success rate  │                                        │
│  │  - Trigger words │                                        │
│  └──────────────────┘                                        │
│                                                              │
│  ┌──────────────────┐  What is true                         │
│  │   KNOWLEDGE      │  Facts about the world and user       │
│  │                  │  "User prefers dark mode"              │
│  │  - Facts         │                                        │
│  │  - Entities      │                                        │
│  │  - Relationships │                                        │
│  │  - Preferences   │                                        │
│  └──────────────────┘                                        │
│                                                              │
│  ┌──────────────────┐  Vector search across all stores      │
│  │   VECTOR INDEX   │  Embedding-based retrieval            │
│  └──────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

### Interface

```python
class Memory:
    """Unified memory interface. Three stores, one API."""

    def __init__(self, db_path: str = "~/.moso/memory.db"): ...

    # --- Experience ---
    def record_experience(self, experience: Experience) -> str: ...
    def get_experience(self, experience_id: str) -> Experience: ...
    def search_experiences(self, query: str, limit: int = 10) -> list[Experience]: ...
    def get_recent_experiences(self, limit: int = 20) -> list[Experience]: ...
    def get_successful_experiences(self, task: str) -> list[Experience]: ...
    def get_failed_experiences(self, task: str) -> list[Experience]: ...

    # --- Skills ---
    def store_skill(self, skill: Skill) -> str: ...
    def get_skill(self, skill_id: str) -> Skill: ...
    def search_skills(self, query: str, limit: int = 5) -> list[Skill]: ...
    def update_skill_stats(self, skill_id: str, success: bool) -> None: ...
    def get_skill_by_trigger(self, trigger: str) -> Skill | None: ...

    # --- Knowledge ---
    def store_fact(self, fact: Fact) -> str: ...
    def get_facts(self, category: str = "general") -> list[Fact]: ...
    def search_knowledge(self, query: str, limit: int = 10) -> list[Fact]: ...
    def store_entity(self, entity: Entity) -> str: ...
    def store_relationship(self, relationship: Relationship) -> str: ...
    def get_entity_graph(self, entity_id: str) -> EntityGraph: ...

    # --- Preferences ---
    def set_preference(self, key: str, value: str, confidence: float = 1.0) -> None: ...
    def get_preference(self, key: str) -> str | None: ...
    def get_all_preferences(self) -> dict[str, str]: ...

    # --- Vector Search ---
    def semantic_search(self, query: str, store: StoreType, limit: int = 10) -> list[SearchResult]: ...
    def hybrid_search(self, query: str, store: StoreType, alpha: float = 0.5) -> list[SearchResult]: ...

    # --- Context ---
    def build_context(self, goal: str, owner_id: str = "default") -> MemoryContext: ...
```

### Models

```python
@dataclass
class Experience:
    id: str
    goal: str                     # What was attempted
    actions: list[ActionRecord]   # What was done
    outcome: Outcome              # What happened
    screen_before: str            # Screenshot hash
    screen_after: str             # Screenshot hash
    duration_ms: int
    timestamp: datetime
    owner_id: str
    tags: list[str]

@dataclass
class ActionRecord:
    action: Action
    result: ActionResult
    observation_before: Observation
    observation_after: Observation

@dataclass
class Skill:
    id: str
    name: str                     # Human-readable name
    description: str              # What this skill does
    steps: list[SkillStep]        # Ordered procedure
    variables: list[SkillVariable]  # Parameterized inputs
    trigger_phrases: list[str]    # Natural language triggers
    success_count: int
    failure_count: int
    success_rate: float
    times_used: int
    last_used: datetime | None
    created_from: list[str]       # Experience IDs that formed this skill
    version: int
    tags: list[str]

@dataclass
class SkillStep:
    order: int
    action_type: ActionType
    command: str
    parameters: dict              # May contain {variable_name} placeholders
    expected_outcome: str
    verification: str             # How to verify this step worked

@dataclass
class SkillVariable:
    name: str                     # e.g., "song_name", "app_name"
    description: str
    default: str | None
    required: bool

@dataclass
class Fact:
    id: str
    content: str                  # "User prefers dark mode"
    category: str                 # preference | system | project | general
    confidence: float
    source: str                   # conversation | observation | inference
    created_at: datetime
    updated_at: datetime

@dataclass
class MemoryContext:
    experiences: list[Experience]
    skills: list[Skill]
    facts: list[Fact]
    preferences: dict[str, str]
    summary: str                  # LLM-friendly context string
```

### Database Schema

```sql
-- Experience Store
CREATE TABLE experiences (
    id              TEXT PRIMARY KEY,
    goal            TEXT NOT NULL,
    actions         TEXT NOT NULL DEFAULT '[]',     -- JSON: list[ActionRecord]
    outcome         TEXT NOT NULL DEFAULT '{}',     -- JSON: Outcome
    screen_before   TEXT,
    screen_after    TEXT,
    duration_ms     INTEGER DEFAULT 0,
    timestamp       TEXT NOT NULL,
    owner_id        TEXT NOT NULL DEFAULT 'default',
    tags            TEXT NOT NULL DEFAULT '[]',     -- JSON: list[str]
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_exp_owner ON experiences(owner_id);
CREATE INDEX idx_exp_timestamp ON experiences(timestamp DESC);
CREATE INDEX idx_exp_goal ON experiences(goal);

-- Skill Store
CREATE TABLE skills (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    steps           TEXT NOT NULL DEFAULT '[]',     -- JSON: list[SkillStep]
    variables       TEXT NOT NULL DEFAULT '[]',     -- JSON: list[SkillVariable]
    trigger_phrases TEXT NOT NULL DEFAULT '[]',     -- JSON: list[str]
    success_count   INTEGER DEFAULT 0,
    failure_count   INTEGER DEFAULT 0,
    success_rate    REAL DEFAULT 0.0,
    times_used      INTEGER DEFAULT 0,
    last_used       TEXT,
    created_from    TEXT NOT NULL DEFAULT '[]',     -- JSON: list[str] experience IDs
    version         INTEGER DEFAULT 1,
    tags            TEXT NOT NULL DEFAULT '[]',     -- JSON: list[str]
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_skill_name ON skills(name);
CREATE INDEX idx_skill_trigger ON skills(trigger_phrases);

-- Knowledge Store
CREATE TABLE facts (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    confidence  REAL DEFAULT 1.0,
    source      TEXT DEFAULT 'conversation',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_fact_category ON facts(category);

CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT DEFAULT 'unknown',
    description TEXT DEFAULT '',
    aliases     TEXT NOT NULL DEFAULT '[]',
    metadata    TEXT NOT NULL DEFAULT '{}',
    confidence  REAL DEFAULT 1.0,
    source      TEXT DEFAULT '',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE relationships (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL REFERENCES entities(id),
    target_id   TEXT NOT NULL REFERENCES entities(id),
    type        TEXT DEFAULT 'related_to',
    label       TEXT DEFAULT '',
    weight      REAL DEFAULT 1.0,
    confidence  REAL DEFAULT 1.0,
    source      TEXT DEFAULT '',
    evidence    TEXT NOT NULL DEFAULT '[]',
    created_at  REAL NOT NULL
);

-- Preferences Store
CREATE TABLE preferences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    confidence  REAL DEFAULT 1.0,
    owner_id    TEXT NOT NULL DEFAULT 'default',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(key, owner_id)
);

-- Vector Index
CREATE TABLE vector_entries (
    id         TEXT PRIMARY KEY,
    store_type TEXT NOT NULL,     -- experience | skill | knowledge
    ref_id     TEXT NOT NULL,     -- ID in the source store
    text       TEXT NOT NULL,
    embedding  TEXT,              -- JSON: list[float]
    created_at REAL NOT NULL
);
CREATE VIRTUAL TABLE vector_entries_fts USING fts5(
    id, store_type, text, content=vector_entries, content_rowid=rowid
);
```

---

## Organ 5: LEARNING

**Responsibility:** Convert experience into skills. Improve skills through repetition. Learn from failures. This is a first-class subsystem, not a plugin.

### Sub-Engines

```
┌─────────────────────────────────────────────────────────────────┐
│                         LEARNING                                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. EXPERIENCE ENGINE                                     │   │
│  │  Records every action with full context.                  │   │
│  │  Input: Action + Observation before + Observation after   │   │
│  │  Output: Experience (stored in Memory.Experience)         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  2. REFLECTION ENGINE                                     │   │
│  │  Analyzes why things succeeded or failed.                 │   │
│  │  Input: Experience + ExecutionResult                      │   │
│  │  Output: Reflection (root cause, patterns, suggestions)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  3. SKILL BUILDER                                         │   │
│  │  Extracts reusable procedures from successful experiences.│   │
│  │  Input: Multiple successful Experiences for same goal     │   │
│  │  Output: Skill (stored in Memory.Skills)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  4. GENERALIZATION ENGINE                                 │   │
│  │  Replaces constants with variables in skills.             │   │
│  │  Input: Skill with hardcoded values                       │   │
│  │  Output: Skill with {variable} placeholders               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  5. OPTIMIZER                                             │   │
│  │  Improves existing skills based on execution history.     │   │
│  │  Input: Skill + recent Experiences using that skill       │   │
│  │  Output: Updated Skill (better steps, fewer failures)     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  6. CURRICULUM ENGINE                                     │   │
│  │  Prioritizes what to learn next.                          │   │
│  │  Input: All failed experiences, all low-success skills    │   │
│  │  Output: Ranked list of learning targets                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  7. EVALUATION ENGINE                                     │   │
│  │  Tests skill quality before deploying to production.      │   │
│  │  Input: New or updated Skill                              │   │
│  │  Output: EvaluationReport (quality score, readiness)      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Interface

```python
class Learning:
    """Learning subsystem. Seven engines, one purpose: get better."""

    def __init__(self, memory: "Memory", brain: "Brain", eyes: "Eyes"): ...

    @property
    def experience_engine(self) -> ExperienceEngine: ...
    @property
    def reflection_engine(self) -> ReflectionEngine: ...
    @property
    def skill_builder(self) -> SkillBuilder: ...
    @property
    def generalization_engine(self) -> GeneralizationEngine: ...
    @property
    def optimizer(self) -> Optimizer: ...
    @property
    def curriculum_engine(self) -> CurriculumEngine: ...
    @property
    def evaluation_engine(self) -> EvaluationEngine: ...

    # --- High-level API ---
    def after_action(self, experience: Experience, result: ExecutionResult) -> LearningOutcome: ...
    def before_action(self, goal: str) -> Skill | None: ...
    def get_learning_targets(self) -> list[LearningTarget]: ...
```

### Sub-Engine Interfaces

```python
class ExperienceEngine:
    """Records every action with full context."""

    def record(
        self,
        goal: str,
        actions: list[ActionRecord],
        outcome: Outcome,
        screen_before: str,
        screen_after: str,
    ) -> Experience: ...

    def record_step(
        self,
        experience_id: str,
        action: ActionRecord,
    ) -> None: ...


class ReflectionEngine:
    """Analyzes why things succeeded or failed."""

    def reflect(self, experience: Experience, result: ExecutionResult) -> Reflection: ...
    def diagnose_failure(self, experience: Experience) -> FailureDiagnosis: ...
    def find_patterns(self, failures: list[Experience]) -> list[FailurePattern]: ...
    def suggest_improvement(self, reflection: Reflection) -> ImprovementSuggestion: ...


class SkillBuilder:
    """Extracts reusable procedures from successful experiences."""

    def should_create_skill(self, task: str) -> bool: ...
    def extract_skill(self, experiences: list[Experience]) -> Skill: ...
    def merge_skills(self, skill_a: Skill, skill_b: Skill) -> Skill: ...
    def validate_skill(self, skill: Skill) -> SkillValidation: ...


class GeneralizationEngine:
    """Replaces constants with variables in skills."""

    def generalize(self, skill: Skill) -> Skill: ...
    def detect_constants(self, experiences: list[Experience]) -> list[Constant]: ...
    def create_variable(self, constant: Constant, values: list[str]) -> SkillVariable: ...


class Optimizer:
    """Improves existing skills based on execution history."""

    def optimize(self, skill: Skill, experiences: list[Experience]) -> Skill: ...
    def remove_failing_steps(self, skill: Skill) -> Skill: ...
    def reorder_steps(self, skill: Skill, experiences: list[Experience]) -> Skill: ...
    def calculate_confidence(self, skill: Skill) -> float: ...


class CurriculumEngine:
    """Prioritizes what to learn next."""

    def get_targets(self) -> list[LearningTarget]: ...
    def rank_by_impact(self, targets: list[LearningTarget]) -> list[LearningTarget]: ...
    def suggest_practice(self) -> list[PracticeTask]: ...


class EvaluationEngine:
    """Tests skill quality before deployment."""

    def evaluate(self, skill: Skill) -> EvaluationReport: ...
    def test_skill(self, skill: Skill, test_cases: list[TestCase]) -> TestResults: ...
    def readiness_check(self, skill: Skill) -> bool: ...
```

### Models

```python
@dataclass
class LearningOutcome:
    experience: Experience
    reflection: Reflection | None
    new_skill: Skill | None
    updated_skill: Skill | None
    learning_target: LearningTarget | None

@dataclass
class FailurePattern:
    pattern_id: str
    description: str
    occurrences: int
    affected_skills: list[str]
    root_cause: str
    suggested_fix: str

@dataclass
class LearningTarget:
    target_type: str               # skill_creation | skill_improvement | failure_prevention
    description: str
    priority: int                  # 1 = highest
    estimated_impact: float        # 0.0 - 1.0
    related_experiences: list[str]
    related_skills: list[str]

@dataclass
class SkillValidation:
    valid: bool
    issues: list[str]
    suggestions: list[str]

@dataclass
class EvaluationReport:
    skill_id: str
    quality_score: float           # 0.0 - 1.0
    ready_for_use: bool
    test_results: list[TestCaseResult]
    recommendations: list[str]

@dataclass
class Constant:
    value: str
    positions: list[int]           # Which steps contain this value
    is_unique: bool                # Only appears in this context
```

### Database Schema

```sql
-- Reflections
CREATE TABLE reflections (
    id                  TEXT PRIMARY KEY,
    experience_id       TEXT NOT NULL REFERENCES experiences(id),
    root_cause          TEXT NOT NULL,
    what_worked         TEXT NOT NULL DEFAULT '[]',  -- JSON: list[str]
    what_failed         TEXT NOT NULL DEFAULT '[]',  -- JSON: list[str]
    improvement         TEXT DEFAULT '',
    failure_pattern     TEXT,
    should_create_skill INTEGER DEFAULT 0,
    created_at          TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_reflect_experience ON reflections(experience_id);

-- Failure Patterns
CREATE TABLE failure_patterns (
    id              TEXT PRIMARY KEY,
    description     TEXT NOT NULL,
    occurrences     INTEGER DEFAULT 1,
    affected_skills TEXT NOT NULL DEFAULT '[]',  -- JSON: list[str]
    root_cause      TEXT NOT NULL,
    suggested_fix   TEXT NOT NULL,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL
);

-- Learning Targets
CREATE TABLE learning_targets (
    id                  TEXT PRIMARY KEY,
    target_type         TEXT NOT NULL,
    description         TEXT NOT NULL,
    priority            INTEGER DEFAULT 5,
    estimated_impact    REAL DEFAULT 0.5,
    related_experiences TEXT NOT NULL DEFAULT '[]',
    related_skills      TEXT NOT NULL DEFAULT '[]',
    status              TEXT NOT NULL DEFAULT 'pending',  -- pending | in_progress | completed
    created_at          TEXT DEFAULT (datetime('now'))
);

-- Evaluation Results
CREATE TABLE evaluations (
    id              TEXT PRIMARY KEY,
    skill_id        TEXT NOT NULL REFERENCES skills(id),
    quality_score   REAL NOT NULL,
    ready_for_use   INTEGER NOT NULL,
    test_results    TEXT NOT NULL DEFAULT '[]',  -- JSON
    recommendations TEXT NOT NULL DEFAULT '[]',  -- JSON
    created_at      TEXT DEFAULT (datetime('now'))
);
```

---

## Organ 6: SAFETY

**Responsibility:** Permissions, risk scoring, privacy, identity, confirmation before dangerous actions.

### Interface

```python
class Safety:
    """Safety engine. Checks permissions, scores risk, protects privacy."""

    def __init__(self, memory: "Memory"): ...

    # --- Risk ---
    def assess_risk(self, action: Action) -> RiskReport: ...
    def check_and_block(self, action: Action) -> tuple[bool, RiskReport]: ...

    # --- Permissions ---
    def check_permission(self, action: Action, identity: IdentityLevel) -> bool: ...
    def require_confirmation(self, action: Action) -> bool: ...

    # --- Identity ---
    def verify_identity(self, signals: IdentitySignals) -> IdentityResult: ...
    def get_identity_level(self) -> IdentityLevel: ...

    # --- Privacy ---
    def scan_for_secrets(self, text: str) -> list[SecretMatch]: ...
    def check_data_exposure(self, action: Action) -> PrivacyAssessment: ...

    # --- Guardrails ---
    def check_prompt(self, prompt: str) -> GuardResult: ...
    def sanitize_output(self, text: str) -> str: ...
```

### Module Mapping

| Current Module | Maps To |
|---------------|---------|
| `moso_core/risk/` | `Safety` (risk scoring, privacy, reputation) |
| `moso_core/safety/` | `Safety` (prompt guard, output guard) |
| `moso_core/identity/` | `Safety` (identity verification) |

---

## Organ 7: UI

**Responsibility:** User interaction. Voice, desktop orb, chat, status display.

### Interface

```python
class UI:
    """User interface. Communicates with user, never with hardware."""

    def __init__(self, brain: "Brain"): ...

    # --- Chat ---
    def send_message(self, text: str) -> None: ...
    def receive_message(self) -> str: ...

    # --- Voice ---
    def start_listening(self) -> None: ...
    def stop_listening(self) -> None: ...
    def speak(self, text: str) -> None: ...

    # --- Status ---
    def update_state(self, state: UIState) -> None: ...
    def show_progress(self, plan: Plan) -> None: ...
    def show_error(self, error: str) -> None: ...
    def show_warning(self, warning: str) -> None: ...

    # --- Confirmation ---
    def ask_confirmation(self, action: Action, risk: RiskReport) -> bool: ...
    def ask_clarification(self, question: str) -> str: ...
```

### Module Mapping

| Current Module | Maps To |
|---------------|---------|
| `moso_ui/` | `UI` (Aura orb, chat, tray) |
| `moso_core/voice/` | `UI` (voice pipeline) |

---

## Event Flow

### Primary Loop: Goal → Skill

```
User: "Play Believer by Imagine Dragons"
        │
        ▼
    ┌─────────┐
    │   UI    │ Receives user input
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │  Brain  │ Calls Memory.search_skills("play believer")
    └────┬────┘
         │
    ┌────┴────────────────────────────────┐
    │                                      │
    │  Skill Found?                        │
    │  YES ──────────────────┐             │
    │  NO ───────┐           │             │
    │            │           │             │
    │            ▼           │             │
    │     ┌────────────┐     │             │
    │     │ Brain.plan │     │             │
    │     │ (new seq)  │     │             │
    │     └─────┬──────┘     │             │
    │           │            │             │
    │           ▼            ▼             │
    │     ┌──────────────────────┐         │
    │     │    Safety.assess()   │         │
    │     │    Risk: LOW ✓       │         │
    │     └──────────┬───────────┘         │
    │                │                     │
    │                ▼                     │
    │     ┌──────────────────────┐         │
    │     │   Muscles.execute()  │         │
    │     │   Open Spotify       │         │
    │     │   Search "Believer"  │         │
    │     │   Click play         │         │
    │     └──────────┬───────────┘         │
    │                │                     │
    │                ▼                     │
    │     ┌──────────────────────┐         │
    │     │   Eyes.diff()        │         │
    │     │   Screen changed     │         │
    │     │   Song playing ✓     │         │
    │     └──────────┬───────────┘         │
    │                │                     │
    │                ▼                     │
    │     ┌──────────────────────┐         │
    │     │ Learning.after_action│         │
    │     │ Record experience    │         │
    │     │ Reflect on success   │         │
    │     │ Skill already exists │         │
    │     │ → Update stats       │         │
    │     └──────────┬───────────┘         │
    │                │                     │
    │                ▼                     │
    │          UI: "Playing Believer"      │
    │                                      │
    └──────────────────────────────────────┘
```

### Skill Creation Flow

```
User: "Create a Python project called data-pipeline"
        │
        ▼
    Brain: No skill found for "create python project"
        │
        ▼
    Brain: Plan steps manually
        │
        ├── Step 1: filesystem.mkdir("data-pipeline")
        ├── Step 2: filesystem.write("data-pipeline/__init__.py", "")
        ├── Step 3: filesystem.write("data-pipeline/main.py", "...")
        └── Step 4: terminal("cd data-pipeline && python -c 'import main'")
        │
        ▼
    All steps succeed
        │
        ▼
    Learning.after_action()
        │
        ├── Experience recorded (3rd success for this pattern)
        │
        ▼
    SkillBuilder.should_create_skill() → True (3+ successes)
        │
        ▼
    SkillBuilder.extract_skill()
        │
        ├── Steps extracted
        ├── GeneralizationEngine generalizes:
        │     "data-pipeline" → {project_name}
        │     "main.py" → stays literal (it's always main.py)
        │
        ▼
    Skill created:
        name: "create_python_project"
        steps:
          1. filesystem.mkdir({project_name})
          2. filesystem.write({project_name}/__init__.py, "")
          3. filesystem.write({project_name}/main.py, "...")
        variables:
          - name: project_name
            required: true
        trigger_phrases: ["create python project", "new python app", ...]
        │
        ▼
    EvaluationEngine.evaluate()
        │
        ├── Quality score: 0.85
        ├── Ready for use: True
        │
        ▼
    Memory.store_skill(skill)
```

### Failure Learning Flow

```
User: "Open Chrome and search for Python tutorials"
        │
        ▼
    Brain: Skill found → "open_app_and_search"
        │
        ▼
    Muscles.execute()
        │
        ├── Step 1: app.launch("chrome") → SUCCESS
        └── Step 2: browser.search("Python tutorials") → FAIL (Chrome not responding)
        │
        ▼
    Brain.reflect()
        │
        ├── Root cause: Chrome launched but not ready for input
        ├── Failure pattern: "app_launch_timing"
        │
        ▼
    Learning.reflection_engine.diagnose_failure()
        │
        ├── Pattern found: "app_launch_timing" (2nd occurrence)
        ├── Suggestion: Add delay after app launch
        │
        ▼
    Learning.optimizer.optimize(skill)
        │
        ├── Step 2 now has: wait(2000ms) before browser.search
        ├── Skill version incremented
        │
        ▼
    Memory.update_skill(skill)
```

---

## Folder Structure

```
moso_core/
├── brain/                          # Organ 1: Reasoning
│   ├── __init__.py
│   ├── planner.py                  # Goal decomposition
│   ├── reasoner.py                 # Step selection, logic
│   ├── reflection.py               # Outcome analysis (delegates to Learning)
│   ├── verifier.py                 # Result verification
│   └── models.py                   # Plan, PlanStep, ExecutionResult, Reflection
│
├── eyes/                           # Organ 2: Observation
│   ├── __init__.py
│   ├── screen.py                   # Screenshot capture, OCR
│   ├── ui_detection.py             # UI element detection
│   ├── window_detection.py         # Window state
│   ├── system_watch.py             # System monitoring
│   ├── diff.py                     # State comparison
│   └── models.py                   # Observation, UIElement, ScreenText, etc.
│
├── muscles/                        # Organ 3: Action
│   ├── __init__.py
│   ├── mouse.py                    # Mouse control
│   ├── keyboard.py                 # Keyboard control
│   ├── browser.py                  # Browser automation
│   ├── shell.py                    # Shell/terminal execution
│   ├── filesystem.py               # File operations
│   ├── clipboard.py                # Clipboard access
│   └── models.py                   # Action, ActionResult, ActionType
│
├── memory/                         # Organ 4: Storage
│   ├── __init__.py
│   ├── experience_store.py         # Experience CRUD
│   ├── skill_store.py              # Skill CRUD
│   ├── knowledge_store.py          # Facts, entities, relationships
│   ├── preference_store.py         # User preferences
│   ├── vector_index.py             # Embedding-based search
│   ├── context_builder.py          # MemoryContext assembly
│   ├── schema.py                   # Database initialization
│   └── models.py                   # Experience, Skill, Fact, etc.
│
├── learning/                       # Organ 5: Self-improvement
│   ├── __init__.py
│   ├── experience_engine.py        # Record actions with context
│   ├── reflection_engine.py        # Analyze success/failure
│   ├── skill_builder.py            # Extract reusable procedures
│   ├── generalization_engine.py    # Constants → variables
│   ├── optimizer.py                # Improve existing skills
│   ├── curriculum_engine.py        # What to learn next
│   ├── evaluation_engine.py        # Test skill quality
│   └── models.py                   # LearningTarget, Reflection, etc.
│
├── safety/                         # Organ 6: Protection
│   ├── __init__.py
│   ├── risk_engine.py              # Risk scoring
│   ├── privacy_engine.py           # Data exposure analysis
│   ├── reputation.py               # Domain/IP reputation
│   ├── permissions.py              # Permission levels
│   ├── identity.py                 # Identity verification
│   ├── guardrails.py               # Prompt/output guard
│   └── models.py                   # RiskReport, IdentityResult, etc.
│
├── ui/                             # Organ 7: Interface
│   ├── __init__.py
│   ├── orb.py                      # Aura floating orb
│   ├── chat.py                     # Conversation bubble
│   ├── voice_ui.py                 # Voice interaction
│   ├── status.py                   # Status display
│   ├── tray.py                     # System tray
│   └── models.py                   # UIState, Message, etc.
│
├── inference/                      # Model backends (shared)
│   ├── base.py
│   ├── llama_cpp/
│   └── onnx_runtime/
│
├── llm/                            # LLM integration (shared)
│   ├── manager.py
│   ├── providers/
│   └── models.py
│
├── resources/                      # System monitoring (shared)
│   ├── manager.py
│   └── models.py
│
├── orchestration/                  # Central hub
│   └── orchestrator.py             # Connects all organs
│
├── desktop/                        # Desktop agent (legacy, to be migrated)
│
├── realtime/                       # Web research (legacy, to be migrated)
│
├── voice/                          # Voice pipeline (legacy, to be migrated)
│
└── system_intelligence/            # System intelligence (legacy, to be migrated)
```

---

## Migration Plan

### Phase 1: Foundation (Weeks 1–2)

| Task | Source | Target | Effort |
|------|--------|--------|--------|
| Create `moso_core/memory/` new schema | `memory/` + `realtime/knowledge_graph.py` | `memory/` (new) | 3 days |
| Create `moso_core/learning/` | New | `learning/` | 5 days |
| Create `moso_core/brain/` | `agents/` + `desktop/vision_planner.py` | `brain/` | 3 days |
| Create `moso_core/eyes/` | `vision/` + `desktop/perception.py` + `system_intelligence/` | `eyes/` | 2 days |
| Create `moso_core/muscles/` | `tools/` + `computer_use/` + `desktop/action_executor.py` | `muscles/` | 2 days |
| Create `moso_core/safety/` | `risk/` + `safety/` + `identity/` | `safety/` | 2 days |
| Create `moso_core/ui/` | `moso_ui/` + `voice/` | `ui/` | 2 days |

### Phase 2: Integration (Weeks 3–4)

| Task | Description | Effort |
|------|-------------|--------|
| Wire Learning → Memory | Experience/Skill/Knowledge stores connected | 1 day |
| Wire Brain → Learning | Brain calls Learning.after_action() after execution | 1 day |
| Wire Eyes → Brain | Observations flow to Brain for reasoning | 1 day |
| Wire Safety → Brain | Risk checks before every action | 1 day |
| Wire UI → Brain | User input → Brain → UI output | 1 day |
| Orchestrator rewrite | New Orchestrator connecting all 7 organs | 3 days |

### Phase 3: Learning Loop (Weeks 5–6)

| Task | Description | Effort |
|------|-------------|--------|
| Experience Engine | Record every action with context | 1 day |
| Reflection Engine | Analyze success/failure patterns | 2 days |
| Skill Builder | Extract skills from 3+ successful experiences | 2 days |
| Generalization Engine | Detect constants, create variables | 1 day |
| Optimizer | Improve skills from execution history | 1 day |
| Curriculum Engine | Rank learning targets by impact | 1 day |
| Evaluation Engine | Test skill quality before use | 1 day |

### Phase 4: Migration (Weeks 7–8)

| Task | Description | Effort |
|------|-------------|--------|
| Migrate legacy modules | `desktop/`, `realtime/`, `voice/`, `system_intelligence/` → new organs | 5 days |
| Remove old `agents/`, `tools/`, `vision/`, `risk/` | Replaced by new organs | 1 day |
| Update orchestrator | Final integration pass | 1 day |
| Update tests | All 249 tests must pass | 2 days |

---

## Docker Integration

```yaml
# docker-compose.yml
version: '3.8'

services:
  moso:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - moso-data:/root/.moso
      - moso-models:/app/models
    environment:
      - MOSO_DB_PATH=/root/.moso/memory.db
      - MOSO_MODEL_PATH=/app/models
      - MOSO_LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  moso-data:
  moso-models:
```

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY moso_core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY moso_core/ ./moso_core/
COPY moso_ui/ ./moso_ui/
COPY run.py .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "moso_core.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Integration Points Summary

| From | To | Data | Direction |
|------|-----|------|-----------|
| UI | Brain | User input | Write |
| Brain | Eyes | Observe request | Write |
| Eyes | Brain | Observation | Read |
| Brain | Muscles | Action | Write |
| Muscles | Brain | ActionResult | Read |
| Brain | Safety | Risk check | Write |
| Safety | Brain | RiskReport | Read |
| Brain | Memory | Read skills/experiences | Read |
| Brain | Learning | ExecutionResult | Write |
| Learning | Memory | Store skills/experiences | Write |
| Learning | Brain | Updated skills | Read |
| Brain | UI | Status updates | Write |
| Memory | Brain | MemoryContext | Read |
| Safety | Memory | Identity verification | Read |
| Eyes | Learning | Screen diffs for verification | Read |
| Learning | Safety | Skill risk assessment | Read |

---

## Design Principles

1. **Local-first.** All data in SQLite. No cloud dependency.
2. **Offline-first.** Works without internet. Online enhances.
3. **Modular.** Each organ has a single responsibility.
4. **Event-driven.** Organs communicate through events, not direct calls.
5. **Memory-centric.** Every action is recorded. Every success becomes a skill.
6. **Self-improving.** The Learning subsystem makes MOSO better every day.
7. **Two-person team.** Maintainable by two developers. No microservices.
8. **Low-resource.** Optimized for laptops. Graceful degradation.
9. **Never app-specific.** No Spotify folder, no Chrome folder. Universal reasoning.
10. **Learning is first-class.** Not a plugin. Not an afterthought. The core loop.

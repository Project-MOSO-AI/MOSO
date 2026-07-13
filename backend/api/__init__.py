from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="MOSO orchestrator not initialized")
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize orchestrator on startup, clean up on shutdown."""
    global _orchestrator
    try:
        from moso_core.inference.base import InferenceConfig
        from moso_core.orchestration.orchestrator import Orchestrator

        model_path = os.environ.get("MOSO_MODEL_PATH", "")
        n_ctx = int(os.environ.get("MOSO_N_CTX", "2048"))

        config = InferenceConfig(model_path=model_path, n_ctx=n_ctx)
        _orchestrator = Orchestrator(config)

        # Enable available modules
        _orchestrator.enable_memory()
        _orchestrator.enable_resources()
        _orchestrator.enable_tools()
        _orchestrator.enable_risk_engine()
        _orchestrator.enable_agents()
        _orchestrator.enable_system_intelligence()

        if model_path:
            _orchestrator.enable_llm(model_path=model_path)

        logger.info("MOSO orchestrator initialized")
    except Exception as e:
        logger.warning("Orchestrator init failed (running in degraded mode): %s", e)

    yield

    if _orchestrator:
        try:
            _orchestrator.unload()
        except Exception:
            pass


app = FastAPI(
    title="MOSO AI",
    description="Privacy-first adaptive AI assistant API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    owner_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    elapsed_ms: int

class ExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict = Field(default_factory=dict)
    dry_run: bool = False

class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "episodic"  # episodic | semantic | procedural
    category: str = "general"
    tags: list[str] = Field(default_factory=list)

class MemorySearchRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    limit: int = 10


# ── Health ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    modules = {}
    orch = _orchestrator
    if orch:
        modules = {
            "memory": orch.memory is not None,
            "resources": orch.resources is not None,
            "tools": orch.tools is not None,
            "agents": orch.agents is not None,
            "risk": orch.risk is not None,
            "system_intelligence": orch.system_intelligence is not None,
            "llm": orch.llm is not None,
            "vision": orch.vision is not None,
            "realtime": orch.realtime is not None,
        }
    return {
        "status": "healthy" if orch else "degraded",
        "service": "moso",
        "modules": modules,
    }


# ── Chat ────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    orch = get_orchestrator()
    start = time.time()
    result = orch.process(req.message)
    elapsed = int((time.time() - start) * 1000)
    return ChatResponse(response=result.text, elapsed_ms=elapsed)


# ── Execute (tools) ────────────────────────────────────────────

@app.post("/execute")
async def execute(req: ExecuteRequest):
    orch = get_orchestrator()
    if orch.tools is None:
        raise HTTPException(status_code=503, detail="Tools not enabled")

    from moso_core.tools.models import ToolRequest
    tool_req = ToolRequest(
        tool_name=req.tool_name,
        parameters=req.parameters,
        dry_run=req.dry_run,
    )
    result = orch.tools.execute_tool(tool_req, identity=orch.identity_verifier)
    return result.to_dict()


# ── Plan (agents) ──────────────────────────────────────────────

class PlanRequest(BaseModel):
    goal: str
    requester: str = "owner"

@app.post("/plan")
async def plan(req: PlanRequest):
    orch = get_orchestrator()
    if orch.agents is None:
        raise HTTPException(status_code=503, detail="Agents not enabled")

    summary = orch.agents.plan_and_execute(req.goal, requester=req.requester)
    return {
        "goal": summary.goal.description,
        "status": summary.overall_status.value,
        "tasks": [
            {
                "title": t.title,
                "status": t.status.value,
                "result": t.result,
                "error": t.error,
            }
            for t in summary.goal.tasks if hasattr(summary.goal, 'tasks')
        ],
    }


# ── Memory ──────────────────────────────────────────────────────

@app.post("/memory/store")
async def memory_store(req: MemoryStoreRequest):
    orch = get_orchestrator()
    if orch.memory is None:
        raise HTTPException(status_code=503, detail="Memory not enabled")

    if req.memory_type == "semantic":
        memory_id = orch.memory.store_fact(
            fact=req.content,
            category=req.category,
        )
    elif req.memory_type == "procedural":
        memory_id = orch.memory.store_procedure(
            task_name=req.content,
            tags=req.tags,
        )
    else:
        memory_id = orch.memory.store_event(
            title=req.content[:80],
            description=req.content,
            tags=req.tags,
        )

    return {"id": memory_id, "type": req.memory_type}


@app.post("/memory/search")
async def memory_search(req: MemorySearchRequest):
    orch = get_orchestrator()
    if orch.memory is None:
        raise HTTPException(status_code=503, detail="Memory not enabled")

    types = [req.memory_type] if req.memory_type else None
    results = orch.memory.retrieve_memories(req.query, memory_types=types, limit=req.limit)

    # Serialize results
    serialized = {}
    for mem_type, items in results.items():
        serialized[mem_type] = [
            item.to_dict() if hasattr(item, 'to_dict') else str(item)
            for item in items
        ]
    return serialized


@app.get("/memory/recent")
async def memory_recent(limit: int = 10):
    orch = get_orchestrator()
    if orch.memory is None:
        raise HTTPException(status_code=503, detail="Memory not enabled")

    events = orch.memory.retrieve_recent_events(limit=limit)
    return [e.to_dict() for e in events]


@app.get("/memory/preferences")
async def memory_preferences():
    orch = get_orchestrator()
    if orch.memory is None:
        raise HTTPException(status_code=503, detail="Memory not enabled")

    prefs = orch.memory.retrieve_preferences()
    return {p.category: p.value for p in prefs}


# ── Skills (procedural memory) ─────────────────────────────────

@app.get("/skills")
async def list_skills():
    orch = get_orchestrator()
    if orch.memory is None:
        raise HTTPException(status_code=503, detail="Memory not enabled")

    results = orch.memory.retrieve_memories("", memory_types=["procedural"], limit=100)
    skills = results.get("procedural", [])
    return [s.to_dict() if hasattr(s, 'to_dict') else str(s) for s in skills]


# ── System ──────────────────────────────────────────────────────

@app.get("/system")
async def system_status():
    orch = get_orchestrator()
    if orch.resources is None:
        raise HTTPException(status_code=503, detail="Resources not enabled")

    status = orch.resources.get_system_status()
    return status.to_dict() if hasattr(status, 'to_dict') else str(status)


@app.get("/system/hardware")
async def system_hardware():
    orch = get_orchestrator()
    if orch.system_intelligence is None:
        raise HTTPException(status_code=503, detail="System intelligence not enabled")

    return {"summary": orch.system_intelligence.get_hardware_summary()}


@app.get("/system/software")
async def system_software():
    orch = get_orchestrator()
    if orch.system_intelligence is None:
        raise HTTPException(status_code=503, detail="System intelligence not enabled")

    return {"summary": orch.system_intelligence.get_software_summary()}


@app.get("/system/diagnostics")
async def system_diagnostics():
    orch = get_orchestrator()
    if orch.system_intelligence is None:
        raise HTTPException(status_code=503, detail="System intelligence not enabled")

    issues = orch.system_intelligence.run_diagnostics()
    return [
        {
            "component": i.component,
            "severity": i.severity,
            "explanation": i.explanation,
            "suggestion": i.suggestion,
        }
        for i in issues
    ]


# ── Identity ────────────────────────────────────────────────────

@app.get("/identity")
async def identity_status():
    orch = get_orchestrator()
    return {
        "enabled": orch.identity_verifier is not None,
        "confidence": orch.get_identity_confidence(),
        "level": str(orch.get_identity_level()) if orch.get_identity_level() else None,
        "is_owner": orch.is_owner(),
    }

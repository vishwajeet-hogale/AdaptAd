"""
Evolution routes.

POST /api/evolve            Start a new GA evolution job (returns job_id).
GET  /api/evolve/{job_id}   Get evolution status and results.
POST /api/chromosome/load   Load a pre-trained chromosome by file path.
GET  /api/chromosomes       List all saved chromosomes.
WS   /ws/evolve/{job_id}    WebSocket for real-time generation updates.
"""

import asyncio
import time
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..ga.engine import GAEngine
from ..ga.storage import list_chromosomes, load_chromosome, load_best_chromosome, save_chromosome
from ..state import Chromosome
from .routes_data import get_users, get_ads, get_content

router = APIRouter(prefix="/api", tags=["evolve"])

# In-memory job store. Key: job_id. Value: dict with status, engine ref, results.
_jobs: dict[str, dict] = {}


class EvolveRequest(BaseModel):
    max_generations: int = 50
    population_size: Optional[int] = None
    seed: int = 42


class LoadChromosomeRequest(BaseModel):
    path: Optional[str] = None  # Load specific file. If None, loads best available.


def _run_evolution(job_id: str, max_generations: int, seed: int):
    """Background task that runs the GA and updates job state."""
    job = _jobs[job_id]
    job["status"] = "running"

    try:
        users = get_users()
        content = get_content()
        ads = get_ads()

        engine = GAEngine(users=users, content_items=content, ad_pool=ads, seed=seed)
        engine.initialize()
        job["engine"] = engine

        for stats in engine.run(max_generations=max_generations):
            job["current_generation"] = stats["generation"]
            job["best_fitness"] = stats["best_fitness"]
            job["history"].append(stats)

            # Push to WebSocket queue if connected.
            ws_queue = job.get("ws_queue")
            if ws_queue is not None:
                try:
                    ws_queue.put_nowait({
                        "type": "generation",
                        "data": stats,
                    })
                except Exception:
                    pass

            if job.get("stop_requested"):
                break

            # Yield briefly so the WebSocket thread can drain the queue
            # and stream each generation live rather than all at once.
            time.sleep(0.05)

        # Save best chromosome.
        if engine.best_chromosome:
            path = save_chromosome(engine.best_chromosome, label=f"job_{job_id[:8]}")
            job["chromosome_path"] = path

        job["status"] = "completed"
        job["best_chromosome"] = (
            engine.best_chromosome.model_dump() if engine.best_chromosome else None
        )

        ws_queue = job.get("ws_queue")
        if ws_queue is not None:
            try:
                ws_queue.put_nowait({
                    "type": "converged",
                    "data": {
                        "final_generation": engine.current_generation,
                        "best_chromosome": engine.best_chromosome.to_vector() if engine.best_chromosome else [],
                        "fitness": engine.best_fitness,
                    },
                })
            except Exception:
                pass

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        ws_queue = job.get("ws_queue")
        if ws_queue is not None:
            try:
                ws_queue.put_nowait({"type": "error", "data": {"message": str(e)}})
            except Exception:
                pass


@router.post("/evolve")
def start_evolution(req: EvolveRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "current_generation": 0,
        "best_fitness": None,
        "history": [],
        "best_chromosome": None,
        "chromosome_path": None,
        "error": None,
        "stop_requested": False,
        "ws_queue": None,
    }
    background_tasks.add_task(_run_evolution, job_id, req.max_generations, req.seed)
    return {"job_id": job_id, "status": "queued"}


@router.get("/evolve/{job_id}")
def get_evolution_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    job = _jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "current_generation": job["current_generation"],
        "best_fitness": job["best_fitness"],
        "history": job["history"],
        "best_chromosome": job["best_chromosome"],
        "chromosome_path": job.get("chromosome_path"),
        "error": job.get("error"),
    }


@router.post("/evolve/{job_id}/stop")
def stop_evolution(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    _jobs[job_id]["stop_requested"] = True
    return {"job_id": job_id, "status": "stop_requested"}


@router.post("/chromosome/load")
def load_chromosome_route(req: LoadChromosomeRequest):
    try:
        if req.path:
            chrom = load_chromosome(req.path)
        else:
            chrom = load_best_chromosome()
        if chrom is None:
            raise HTTPException(status_code=404, detail="No saved chromosomes found.")
        return {"chromosome": chrom.model_dump(), "genes": chrom.to_vector()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chromosomes")
def list_saved_chromosomes():
    saved = list_chromosomes()
    return {"chromosomes": saved, "count": len(saved)}

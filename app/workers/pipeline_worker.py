"""Pipeline worker — processes generation runs from the queue.

Usage: python -m app.workers.pipeline_worker
"""

from __future__ import annotations

import asyncio
import logging
import sys
from uuid import UUID

from app.core.config import get_settings
from app.core.db.model_registry import load_model_metadata
from app.core.db.session import SessionLocal
from app.modules.projects.models import GenerationRun
from app.modules.pipeline.orchestrator import run_pipeline

logger = logging.getLogger("klarnow.pipeline_worker")


async def process_run(run_id: UUID) -> None:
    """Execute a single generation run."""
    load_model_metadata()
    db = SessionLocal()
    try:
        run = db.get(GenerationRun, run_id)
        if not run:
            logger.error("Run %s not found", run_id)
            return
        if run.status not in ("queued", "running"):
            logger.info("Run %s already %s, skipping", run_id, run.status)
            return

        logger.info("Starting pipeline run %s for project %s", run.id, run.project_id)
        await run_pipeline(db, run)
        logger.info("Pipeline run %s completed with status %s", run.id, run.status)
    except Exception:
        logger.exception("Pipeline run %s failed with unhandled error", run_id)
    finally:
        db.close()


def run_single(run_id: str) -> None:
    """Run a single generation job (for CLI / Makefile use)."""
    asyncio.run(process_run(UUID(run_id)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print("Usage: python -m app.workers.pipeline_worker <run_id>")
        sys.exit(1)
    run_single(sys.argv[1])

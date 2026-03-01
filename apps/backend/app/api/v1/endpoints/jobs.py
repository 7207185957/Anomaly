from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError
from rq.job import Job

from app.api.deps import AuthContext, require_auth
from app.core.config import get_settings
from app.core.redis import get_queue, get_redis
from app.schemas.jobs import JobStatusResponse, JobSubmitResponse, RcaJobRequest
from app.services.demo_data_service import DemoDataService

router = APIRouter(prefix="/jobs", tags=["jobs"])
_demo_jobs: dict[str, dict] = {}


@router.post("/rca", response_model=JobSubmitResponse)
def submit_rca_job(req: RcaJobRequest, _: AuthContext = Depends(require_auth)) -> JobSubmitResponse:
    settings = get_settings()
    if settings.demo_mode:
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        _demo_jobs[job_id] = {
            "submitted_at": now,
            "status": "queued",
            "result": DemoDataService().demo_job_result(req.keyword, req.context),
            "error": None,
        }
        return JobSubmitResponse(
            job_id=job_id,
            queue="demo-jobs",
            status="queued",
            submitted_at=now,
        )

    queue = get_queue(settings.rca_queue_name)
    try:
        job = queue.enqueue(
            "app.workers.tasks.run_rca_job",
            keyword=req.keyword,
            context=req.context,
            job_timeout=600,
            result_ttl=86400,
            failure_ttl=86400,
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}")
    return JobSubmitResponse(
        job_id=job.id,
        queue=queue.name,
        status=job.get_status(refresh=True),
        submitted_at=datetime.now(timezone.utc),
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, _: AuthContext = Depends(require_auth)) -> JobStatusResponse:
    settings = get_settings()
    if settings.demo_mode:
        if job_id not in _demo_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        item = _demo_jobs[job_id]
        elapsed = (datetime.now(timezone.utc) - item["submitted_at"]).total_seconds()
        status = "finished" if elapsed >= 2 else "started"
        return JobStatusResponse(
            job_id=job_id,
            status=status,
            result=item["result"] if status == "finished" else None,
            error=item["error"],
        )

    try:
        job = Job.fetch(job_id, connection=get_redis())
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job.get_status(refresh=True)
    result = job.result if status == "finished" else None
    error = job.exc_info if status == "failed" else None
    return JobStatusResponse(job_id=job.id, status=status, result=result, error=error)


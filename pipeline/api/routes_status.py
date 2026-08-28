from fastapi import APIRouter

from pipeline.api.status import get_status

router = APIRouter()


@router.get("/status")
def status() -> dict:
    return get_status()

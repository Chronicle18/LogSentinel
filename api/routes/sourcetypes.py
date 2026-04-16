"""GET /sourcetypes — list registered sourcetype configs and rule counts."""

import structlog
from fastapi import APIRouter, Request

from api.schemas import SourcetypeInfo, SourcetypeListResponse
from configs.loader import ConfigManager

log = structlog.get_logger()

router = APIRouter()


@router.get("/sourcetypes", response_model=SourcetypeListResponse)
async def list_sourcetypes(request: Request):
    config_manager: ConfigManager = request.app.state.config_manager

    sourcetypes = []
    for name, config in config_manager.configs.items():
        sourcetypes.append(
            SourcetypeInfo(
                sourcetype=name,
                rule_count=len(config.transforms),
                config_path=None,
            )
        )

    return SourcetypeListResponse(sourcetypes=sourcetypes)

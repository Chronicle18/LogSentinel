"""POST /validate — dry-run CIM compliance check on a sample log line."""

import structlog
from fastapi import APIRouter, HTTPException, Request

from api.schemas import ValidateRequest, ValidateResponse
from configs.loader import ConfigManager
from parser.validator import Validator

log = structlog.get_logger()

router = APIRouter()


@router.post("/validate", response_model=ValidateResponse)
async def validate_line(payload: ValidateRequest, request: Request):
    config_manager: ConfigManager = request.app.state.config_manager
    config = config_manager.get_config(payload.sourcetype)

    if not config:
        raise HTTPException(
            status_code=422,
            detail={"detail": f"Sourcetype '{payload.sourcetype}' not found",
                    "code": "SOURCETYPE_NOT_REGISTERED"},
        )

    validator = Validator(config)
    result = validator.validate_line(payload.line)

    event_data = {}
    for k, v in result["event"].items():
        event_data[k] = str(v) if v is not None else None

    return ValidateResponse(
        populated_fields=result["populated_fields"],
        missing_fields=result["missing_fields"],
        verdict="pass" if result["pass"] else "fail",
        event=event_data,
    )

"""Private history, analytics, reports, snapshots and schedule editor APIs."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from backend.api.staff_security import teacher, write_teacher
from backend.api.admin_routes import perform
from backend.api import teacher_data as data
from backend.db import database as db
from backend.db.schedule_editor_data import editor_choices
from backend.db.schedule_editor_save import save_editor_schedule
from backend.db.notifications import notification_status
from backend.db.application_policy import get_policy, save_policy

router = APIRouter(prefix="/api/teacher")
T = Annotated[dict, Depends(teacher)]
W = Annotated[dict, Depends(write_teacher)]


class Policy(BaseModel):
    mode: str
    processes: list[str] = Field(max_length=1000)


class NotificationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: StrictInt | None = Field(default=None, gt=0, le=9223372036854775807)


@router.get("/options")
async def options(actor: T):
    return await perform(data.options, actor)


@router.get("/history")
async def history(
    actor: T,
    computer_id: int | None = None,
    user_id: int | None = None,
    class_name: str = "",
    only_hits: bool = False,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await perform(
        data.history, actor, computer_id, user_id, class_name, only_hits, limit, offset
    )


@router.get("/analytics")
async def analytics(
    actor: T,
    computer_id: int | None = None,
    user_id: int | None = None,
    start: str = "",
    end: str = "",
):
    from datetime import date

    try:
        if start:
            date.fromisoformat(start)
        if end:
            date.fromisoformat(end)
        if start and end and start > end:
            raise ValueError("End date must follow start date.")
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(400, "Choose a valid date range.") from exc
    return await perform(data.analytics, actor, computer_id, user_id, start, end)


@router.get("/snapshots/{eid}")
async def snapshot(eid: int, actor: T):
    return await perform(data.snapshot, actor, eid)


@router.get("/reports")
async def reports(actor: T):
    return await perform(data.owned, actor, db.list_runs, 200)


@router.get("/reports/{rid}")
async def report(rid: int, actor: T):
    return await perform(data.report, actor, rid)


@router.get("/reports/{rid}/{kind}")
async def export(rid: int, kind: str, actor: T):
    from backend.services.report_data import export_report

    content = await perform(data.owned, actor, export_report, rid, kind)
    return Response(
        content,
        media_type="application/pdf" if kind == "pdf" else "text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="exam-{rid}.{kind}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/schedules")
async def schedules(actor: T):
    return await perform(data.owned, actor, db.list_schedules)


@router.get("/schedule-options")
async def schedule_options(actor: T, schedule_id: int | None = None):
    return await perform(data.owned, actor, editor_choices, schedule_id)


@router.post("/schedules")
async def create_schedule(payload: dict, actor: W):
    return {"id": await perform(data.owned, actor, save_editor_schedule, payload, actor["id"])}


@router.put("/schedules/{sid}")
async def edit_schedule(sid: int, payload: dict, actor: W):
    return {"id": await perform(data.owned, actor, save_editor_schedule, payload, actor["id"], sid)}


@router.delete("/schedules/{sid}")
async def delete_schedule(sid: int, actor: W):
    await perform(data.owned, actor, db.delete_schedule, sid)
    db.log_action("schedule.delete", user_id=actor["id"], entity="schedule", entity_id=sid)
    return {"ok": True}


@router.get("/policy")
async def policy(actor: T):
    return await perform(get_policy, actor["id"])


@router.put("/policy")
async def edit_policy(payload: Policy, actor: W):
    await perform(save_policy, actor["id"], payload.mode, payload.processes)
    return {"ok": True}


@router.get("/notifications")
async def notifications(actor: T):
    return {
        "rows": await perform(data.owned, actor, db.list_notifications),
        "status": await perform(data.owned, actor, notification_status),
    }


@router.post("/notifications/read")
async def read_notifications(payload: NotificationRead, actor: W):
    if payload.id is None:
        await perform(data.owned, actor, db.mark_all_read)
    else:
        await perform(data.owned, actor, db.mark_read, payload.id)
    return {"ok": True}

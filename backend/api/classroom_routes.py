"""Live classroom grids and stop commands remain owner checked on every request."""

from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.api.staff_security import staff, teacher, write_teacher
from backend.api.admin_security import browser_state
from backend.api.admin_routes import perform
from backend.services.classroom_state import rooms, registry_lock
from backend.services.classroom_monitor import start_classroom, stop_classroom
from backend.db.group_queries import list_groups
from backend.db.workstation_alarms import list_alarms, stop_alarm

router = APIRouter(prefix="/api")


class Room(BaseModel):
    classroom_id: int


@router.get("/classrooms")
async def classrooms(actor: Annotated[dict, Depends(staff)]):
    return await perform(list_groups)


def live_data(gid, actor):
    with registry_lock:
        room = rooms.get(gid)
        occupied = bool(room and (room.monitor or room.stopping))
        visible = (
            room if actor["role"] == "admin" or (room and room.owner_id == actor["id"]) else None
        )
        return {
            "running": occupied,
            "owned": bool(room and room.owner_id == actor["id"]),
            "stopping": bool(room and room.stopping),
            "classroom": room.monitored_group_name if room else None,
            "frames": [
                {
                    "id": i,
                    "name": name,
                    "raw": frame[1],
                    "annotated": frame[0],
                    "detections": frame[2],
                    "online": visible.is_computer_online(name),
                }
                for i, (name, frame) in enumerate(list(visible.latest_frames.items()))
            ]
            if visible and visible.monitor
            else [],
            "computers": visible.computers if visible and visible.monitor else [],
            "logs": list(visible.log_buffer[-100:]) if visible else [],
        }


@router.get("/classrooms/{gid}/live")
async def live(gid: int, actor: Annotated[dict, Depends(staff)]):
    return await perform(live_data, gid, actor)


@router.post("/teacher/exam/start")
async def start(payload: Room, actor: Annotated[dict, Depends(write_teacher)]):
    await perform(start_classroom, payload.classroom_id, actor["id"])
    browser_state()["classroom_id"] = payload.classroom_id
    return {"ok": True}


@router.post("/teacher/exam/stop")
async def stop(payload: Room, actor: Annotated[dict, Depends(write_teacher)]):
    await perform(stop_classroom, payload.classroom_id, actor["id"])
    return {"ok": True}


@router.get("/teacher/alarms")
async def alarms(actor: Annotated[dict, Depends(teacher)]):
    return await perform(list_alarms, actor["id"])


@router.post("/teacher/alarms/{aid}/stop")
async def silence(aid: int, actor: Annotated[dict, Depends(write_teacher)]):
    await perform(stop_alarm, actor["id"], aid)
    return {"ok": True}

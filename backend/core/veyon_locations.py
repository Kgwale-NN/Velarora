"""Group Veyon directory objects by parent ID, list order, or flat fallback."""
from typing import Optional


def _uid(o: dict) -> str:
    """Normalize a UID: strip surrounding braces, lowercase."""
    raw = o.get("Uid") or o.get("uid") or o.get("UID") or ""
    return raw.strip("{}").lower()

def _parent_uid(o: dict) -> str:
    raw = o.get("ParentUid") or o.get("parentUid") or o.get("ParentUID") or ""
    return raw.strip("{}").lower()

def _comp(o: dict) -> Optional[dict]:
    host = o.get("HostAddress") or o.get("hostAddress") or ""
    if not host:
        return None
    return {
        "name": o.get("Name") or o.get("name") or host,
        "host": host,
    }


def by_parent(objects: list[dict]) -> list[dict]:
    # ── Strategy 1: Uid / ParentUid (normalized) ─────────────────────────────
    # Veyon uses Type 2 for locations (rooms/groups) and Type 3 for computers.
    # Type 1 was used in older Veyon versions — check both to be safe.
    locs: dict[str, dict] = {}
    for o in objects:
        if o.get("Type") in (1, 2):
            uid = _uid(o)
            if uid:
                locs[uid] = {
                    "name": o.get("Name") or o.get("name") or "Unknown",
                    "computers": [],
                }
    for o in objects:
        if o.get("Type") == 3:
            comp = _comp(o)
            if not comp:
                continue
            parent = _parent_uid(o)
            if parent in locs:
                locs[parent]["computers"].append(comp)
    result = [v for v in locs.values() if v["computers"]]
    return result


def by_order(objects: list[dict]) -> list[dict]:
    # ── Strategy 2: sequential — each computer goes to the nearest PRECEDING
    #    location in the array.  Works even when all locations are listed before
    #    all computers, by tracking position explicitly. ────────────────────────
    loc_list: list[tuple[int, dict]] = []
    for i, o in enumerate(objects):
        if o.get("Type") in (1, 2):
            loc = {
                "name": o.get("Name") or o.get("name") or "Unknown",
                "computers": [],
            }
            loc_list.append((i, loc))

    if loc_list:
        for i, o in enumerate(objects):
            if o.get("Type") != 3:
                continue
            comp = _comp(o)
            if not comp:
                continue
            # Assign to the location whose index is closest to (but ≤) this
            # computer's index.  If computer appears BEFORE all locations (edge
            # case), assign to the first location.
            target = loc_list[0][1]
            for pos, loc in loc_list:
                if pos <= i:
                    target = loc
                else:
                    break
            target["computers"].append(comp)
        result = [loc for _, loc in loc_list if loc["computers"]]
        if result:
            return result

    return []


def group_locations(objects: list[dict]) -> list[dict]:
    result = by_parent(objects) or by_order(objects)
    if result:
        return result
    computers = [_comp(o) for o in objects if o.get("Type") == 3]
    computers = [c for c in computers if c]
    return [{"name": "Imported", "computers": computers}] if computers else []

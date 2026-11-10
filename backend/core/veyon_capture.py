"""Fetch screen images and the logged-in user from Veyon."""
from typing import Optional
import cv2
import numpy as np
import requests


def grab_framebuffer(
    session:  requests.Session,
    base_url: str,
    conn_uid: str,
    fmt:      str,
    quality:  int,
    width:    int,
) -> Optional[bytes]:
    params: dict = {"format": fmt, "quality": quality}
    if width:
        params["width"] = width
    try:
        r = session.get(
            f"{base_url}/framebuffer",
            params=params,
            headers={"Connection-Uid": conn_uid},
            timeout=5,
        )
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content
    except requests.RequestException:
        pass
    return None


def get_logged_user(
    session:  requests.Session,
    base_url: str,
    conn_uid: str,
) -> Optional[str]:
    """
    Return the OS login name of the user currently active on the
    monitored computer, or None if unavailable.
    Veyon WebAPI endpoint: GET /user  → {"login": "...", "fullName": "..."}
    """
    try:
        r = session.get(
            f"{base_url}/user",
            headers={"Connection-Uid": conn_uid},
            timeout=3,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("login") or data.get("name") or None
    except requests.RequestException:
        pass
    return None


def decode_image(raw: bytes) -> Optional[np.ndarray]:
    if not raw:
        return None
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

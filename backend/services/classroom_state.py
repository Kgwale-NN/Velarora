"""Independent live buffers for one classroom; old global buffers never enter a teacher page."""
import queue
import time
import threading


class ClassroomState:
    LOG_CAP=500
    def __init__(self,room_id,owner_id):
        self.room_id,self.owner_id=room_id,owner_id
        self.monitor=None
        self.stopping=False
        self.monitor_lock=threading.RLock()
        self.log_q=queue.Queue()
        self.img_q=queue.Queue(maxsize=64)
        self.latest_frames={}
        self.log_buffer=[]
        self.log_total=0
        self.computer_ids={}
        self.computer_users={}
        self.computer_os_usernames={}
        self.computer_last_frame_ts={}
        self.running_model_id=None
        self.capture_interval=1
        self.monitored_group_name=None
        self.schedule_triggered=False
        self.consecutive_detections={}
        self.computers=[]
        self.schedule_id=None
        self.suppressed_schedule=None
    def is_computer_online(self,name):
        return time.perf_counter()-self.computer_last_frame_ts.get(name,0)<max(10,3*self.capture_interval)


rooms={}
registry_lock=threading.RLock()


def current_room(room_id,owner_id):
    with registry_lock:
        room=rooms.get(room_id)
        return room if room and room.owner_id==owner_id else None

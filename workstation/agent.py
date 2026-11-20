"""Velarora interactive Windows workstation agent. Run in the student's desktop session."""
import argparse
import ctypes
from ctypes import wintypes
import json
import logging
import math
import os
from pathlib import Path
import struct
import tempfile
import time
from urllib.request import Request,urlopen
from urllib.parse import urlparse
import wave
import psutil

log=logging.getLogger('velarora-agent')


def foreground_process():
    ctypes.windll.user32.GetForegroundWindow.restype=wintypes.HWND
    hwnd=ctypes.windll.user32.GetForegroundWindow()
    pid=wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(wintypes.HWND(hwnd),ctypes.byref(pid))
    try:
        name=psutil.Process(pid.value).name().lower()
        return name if name.endswith(".exe") else ""
    except (psutil.Error,ValueError):
        return ''


def make_siren(path):
    rate=16000
    samples=bytearray()
    for i in range(rate*2):
        frequency=850 if i<rate else 1200
        envelope=min(1,i/100,(rate*2-i)/100)
        samples.extend(struct.pack('<h',int(16000*envelope*math.sin(2*math.pi*frequency*i/rate))))
    with wave.open(str(path),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(rate);output.writeframes(samples)


class AlarmPlayer:
    def __init__(self):
        import winsound
        self.audio=winsound
        self.active=False
        self.path=Path(tempfile.gettempdir())/'velarora-workstation-alarm.wav'
        make_siren(self.path)
    def set(self,active):
        if active==self.active:
            return
        if active:
            self.audio.PlaySound(str(self.path),self.audio.SND_FILENAME|self.audio.SND_ASYNC|self.audio.SND_LOOP)
        else:
            self.audio.PlaySound(None,0)
        self.active=active


def run_agent(config):
    url=config['server_url'].rstrip('/')
    parsed=urlparse(url)
    if parsed.scheme!='https' and parsed.hostname not in ('127.0.0.1','localhost','::1'):
        raise ValueError('Use an HTTPS server URL for classroom-network credentials.')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a plain server URL without credentials or query parameters.')
    alarm=AlarmPlayer()
    while True:
        try:
            body=json.dumps({'process':foreground_process(),'alarm_active':alarm.active}).encode()
            req=Request(url+'/api/workstation/heartbeat',data=body,method='POST',
                headers={'Authorization':'Bearer '+config['token'],'Content-Type':'application/json'})
            with urlopen(req,timeout=5) as response:
                desired=json.load(response)
            alarm.set(bool(desired['alarm']))
        except Exception as exc:
            # Keep an already-sounding alarm latched until a verified server reply says stop.
            log.warning('Server connection unavailable: %s',type(exc).__name__)
        time.sleep(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if os.name!='nt':
        raise SystemExit('The workstation agent runs on Windows.')
    run_agent(json.loads(Path(args.config).read_text(encoding='utf-8-sig')))

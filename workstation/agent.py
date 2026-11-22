"""Velarora interactive Windows workstation agent. Run in the student's desktop session."""
import argparse
import ctypes
import getpass
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
from urllib.parse import urlparse, quote
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


def validate_config(config):
    url=config['server_url'].rstrip('/')
    parsed=urlparse(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or (parsed.scheme!='https' and parsed.hostname not in ('127.0.0.1','localhost','::1')):
        raise ValueError('Use an HTTPS server URL for classroom-network credentials.')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a plain server URL without credentials or query parameters.')
    if not config.get('token') or len(config['token']) > 256:
        raise ValueError('Download a valid agent configuration from Workstation setup.')
    return url


def run_agent(config, stop_event=None, status=None):
    url=validate_config(config)
    alarm=AlarmPlayer()
    def report(message, connected=False):
        if status:
            status({'message':message,'connected':connected,'alarm':alarm.active})
    def send(route, body, content_type='application/json', extra=None):
        req=Request(url+'/api/workstation/'+route,data=body,method='POST',
            headers={'Authorization':'Bearer '+config['token'],'Content-Type':content_type,**(extra or {})})
        with urlopen(req,timeout=8) as response:
            return json.load(response)
    while True:
        if stop_event is not None and stop_event.is_set():
            if not alarm.active:
                try:
                    final=send('heartbeat',json.dumps({'process':'','alarm_active':False}).encode())
                    alarm.set(bool(final['alarm']))
                except Exception as exc:
                    log.warning('Final silence acknowledgement unavailable: %s',type(exc).__name__)
                if not alarm.active:
                    report('Disconnected. Screen capture stopped.')
                    return
            stop_event.clear()
        try:
            process=foreground_process()
            capable=bool(config.get('screen_capture'))
            body=json.dumps({'process':process,'alarm_active':alarm.active,'capture_capable':capable}).encode()
            desired=send('heartbeat',body)
            alarm.set(bool(desired['alarm']))
            if capable and desired.get('capture_allowed'):
                from workstation.screens import capture
                raw=capture()
                after=foreground_process()
                send('frame',raw,'image/jpeg',{
                    'X-Velarora-Run':str(desired['capture_run_id']),
                    'X-Velarora-Process':quote(process if process==after else '',safe=''),
                    'X-Velarora-User':quote(getpass.getuser(),safe=''),
                })
                report('Monitoring this PC. All connected screens are being sent.',True)
            else:
                report('Connected. Waiting for the teacher to start an exam.',True)
        except Exception as exc:
            # Keep an already-sounding alarm latched until a verified server reply says stop.
            log.warning('Server connection unavailable: %s',type(exc).__name__)
            report('Connection unavailable. Retrying; an active alarm stays on.')
        if stop_event is not None:
            stop_event.wait(1)
        else:
            time.sleep(1)


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if os.name!='nt':
        raise SystemExit('The workstation agent runs on Windows.')
    run_agent(json.loads(Path(args.config).read_text(encoding='utf-8-sig')))

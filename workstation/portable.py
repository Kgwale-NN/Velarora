"""Visible, consent-based launcher for the portable campus workstation client."""
import argparse
import ctypes
from ctypes import wintypes
import json
import logging
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from workstation.agent import run_agent, validate_config
from workstation import screens


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-test',type=Path)
    args=parser.parse_args()
    if args.self_test:
        import psutil
        from workstation.app_presence import snapshot
        check=tk.Tk()
        check.withdraw()
        check.update_idletasks()
        args.self_test.write_text(json.dumps({'tk':tk.TkVersion,'pillow':bool(screens.capture),
                                             'psutil':psutil.__version__,
                                             'native_verification':snapshot() is not None}),encoding='utf-8')
        check.destroy()
        return
    home=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
    logging.basicConfig(filename=home/'agent.log',level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s')
    root=tk.Tk()
    root.title('Velarora — Campus PC')
    root.geometry('620x370')
    root.minsize(540,370)
    root.configure(bg='#ffffff')
    kernel=ctypes.windll.kernel32
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    mutex=kernel.CreateMutexW(None,False,'Local\\VelaroraWorkstationAgent')
    if not mutex or kernel.GetLastError()==183:
        messagebox.showinfo('Velarora','The workstation agent is already running on this PC.')
        if mutex:
            kernel.CloseHandle(mutex)
        root.destroy()
        return
    try:
        config=json.loads((home/'agent.json').read_text(encoding='utf-8-sig'))
        validate_config(config)
    except Exception:
        messagebox.showerror('Configuration needed',
            'Put the configuration downloaded from Workstation setup next to this app and rename it agent.json.')
        kernel.CloseHandle(mutex)
        root.destroy()
        return
    box=ttk.Frame(root,padding=24)
    box.pack(fill='both',expand=True)
    ttk.Label(box,text='Connect this campus PC',font=('Segoe UI',19,'bold')).pack(anchor='w')
    ttk.Label(box,text=config.get('computer_name','Classroom PC'),font=('Segoe UI',12)).pack(anchor='w',pady=(8,0))
    ttk.Label(box,text=config['server_url'],wraplength=550).pack(anchor='w',pady=(6,16))
    allowed=tk.BooleanVar(value=False)
    consent=ttk.Checkbutton(box,variable=allowed,text='Allow all screens and foreground app names to be sent during the exam.')
    consent.pack(anchor='w')
    ttk.Label(box,text='The teacher can view and save screenshots. An exam alarm can be stopped by the teacher.',
              wraplength=550).pack(anchor='w',pady=(8,16))
    message=tk.StringVar(value='Not connected. Tick the permission box, then press Connect.')
    ttk.Label(box,textvariable=message,wraplength=550).pack(anchor='w',pady=(0,16))
    events=queue.Queue()
    stop=threading.Event()
    state={'alarm':False}
    worker=None
    closing=False
    def work():
        try:
            run_agent(config,stop,events.put)
        except Exception as exc:
            logging.warning('Agent stopped: %s',type(exc).__name__)
            events.put({'message':'Could not start. Check agent.log or ask your administrator.','alarm':False})
    def begin():
        nonlocal worker
        if worker is not None and worker.is_alive():
            return
        if not allowed.get():
            messagebox.showinfo('Permission needed','Please tick the permission box before connecting.')
            return
        stop.clear()
        worker=threading.Thread(target=work,daemon=True)
        worker.start()
        message.set('Connecting…')
    def disconnect():
        if state['alarm']:
            messagebox.showinfo('Exam alarm','Ask the teacher to stop the alarm on their dashboard first.')
        else:
            stop.set()
    def close():
        nonlocal closing
        if state['alarm']:
            disconnect()
            return
        stop.set()
        closing=True
    def tick():
        nonlocal closing
        while not events.empty():
            event=events.get_nowait()
            state.update(event)
            message.set(('ALARM — ask the teacher to stop it. ' if state['alarm'] else '')+event['message'])
        if closing and state['alarm']:
            closing=False
        running=worker is not None and worker.is_alive()
        connect.configure(state='disabled' if running else 'normal')
        consent.configure(state='disabled' if running else 'normal')
        if closing and not running:
            kernel.CloseHandle(mutex)
            root.destroy()
            return
        root.after(250,tick)
    controls=ttk.Frame(box)
    controls.pack(anchor='w')
    connect=ttk.Button(controls,text='Connect',command=begin)
    connect.pack(side='left',padx=(0,12))
    ttk.Button(controls,text='Disconnect',command=disconnect).pack(side='left')
    root.protocol('WM_DELETE_WINDOW',close)
    tick()
    root.mainloop()


if __name__=='__main__':
    main()

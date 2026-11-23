import numpy as np
import torch
from ultralytics.engine.results import Results
from backend.core import app_presence


def result():
    return Results(np.zeros((40,60,3),dtype=np.uint8),path='test.jpg',
                   names={0:'Notepad',1:'Other'},boxes=torch.tensor([[1,1,20,20,.9,0],[22,1,35,20,.8,1]]))


def test_confirmed_closed_notepad_is_removed_before_alerts(monkeypatch):
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:True)
    monkeypatch.setattr(app_presence,'snapshot',lambda:{'notepad.exe':False})
    checked=app_presence.corroborate(result(),1,'localhost')
    assert checked.boxes.cls.tolist()==[1]


def test_real_notepad_detection_is_preserved(monkeypatch):
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:True)
    monkeypatch.setattr(app_presence,'snapshot',lambda:{'notepad.exe':True})
    assert len(app_presence.corroborate(result(),1,'localhost').boxes)==2


def test_remote_pc_never_uses_home_desktop_processes(monkeypatch):
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:False)
    def forbidden():raise AssertionError('Must not inspect server processes for a remote PC')
    monkeypatch.setattr(app_presence,'snapshot',forbidden)
    monkeypatch.setattr(app_presence,'_samples',{})
    app_presence.record(42,{'notepad.exe':False})
    assert len(app_presence.corroborate(result(),42,'agent:remote').boxes)==1
    assert len(app_presence.corroborate(result(),43,'agent:other').boxes)==1


def test_stale_or_missing_evidence_cannot_confirm_a_notepad_alarm(monkeypatch):
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:False)
    monkeypatch.setattr(app_presence,'_samples',{})
    app_presence.record(42,{'notepad.exe':False})
    apps,stamp=app_presence._samples[42]
    app_presence._samples[42]=(apps,stamp-10)
    assert len(app_presence.corroborate(result(),42,'agent:remote').boxes)==1
    app_presence.record(42,None)
    assert app_presence.current(42,'agent:remote') is None


def test_legacy_agent_foreground_notepad_is_positive_evidence(monkeypatch):
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:False)
    monkeypatch.setattr(app_presence,'_samples',{})
    app_presence.record(42,None,'notepad.exe')
    assert len(app_presence.corroborate(result(),42,'agent:remote').boxes)==2


def test_ai_inspects_the_actual_native_window_and_keeps_its_location(monkeypatch):
    from unittest.mock import MagicMock
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:False)
    monkeypatch.setattr(app_presence,'_samples',{})
    monkeypatch.setattr(app_presence,'_regions',{})
    app_presence.record(42,{'notepad.exe':True},windows=[[.5,.25,.9,.8]])
    image=np.zeros((40,60,3),dtype=np.uint8)
    model=MagicMock(return_value=[result()])
    checked=app_presence.refine(result(),42,'agent:remote',model,image,conf=.4)
    assert model.call_args.args[0][0].shape[:2]==(22,24)
    notepad=checked.boxes.data[checked.boxes.cls==0][0]
    assert notepad[:4].tolist()==[30,10,54,32]
    assert abs(float(notepad[4])-.9)<.001


def test_known_hidden_window_cannot_turn_a_browser_panel_into_notepad(monkeypatch):
    from unittest.mock import MagicMock
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:False)
    app_presence.record(42,{'notepad.exe':True},windows=[])
    model=MagicMock()
    checked=app_presence.refine(result(),42,'agent:remote',model,np.zeros((40,60,3),dtype=np.uint8))
    model.assert_not_called()
    assert checked.boxes.cls.tolist()==[1]


def test_current_agent_without_visible_window_cannot_use_dashboard_box(monkeypatch):
    from unittest.mock import MagicMock
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:False)
    monkeypatch.setattr(app_presence,'_samples',{})
    monkeypatch.setattr(app_presence,'_regions',{})
    monkeypatch.setattr(app_presence,'_window_reporting',set())
    app_presence.record(42,{'notepad.exe':True},windows=None)
    model=MagicMock()
    checked=app_presence.refine(result(),42,'agent:remote',model,np.zeros((40,60,3),dtype=np.uint8))
    model.assert_not_called()
    assert checked.boxes.cls.tolist()==[1]


def test_legacy_agent_keeps_visual_detection_when_window_api_is_unavailable(monkeypatch):
    monkeypatch.setattr(app_presence,'local_windows_target',lambda host:False)
    monkeypatch.setattr(app_presence,'_samples',{})
    monkeypatch.setattr(app_presence,'_regions',{})
    monkeypatch.setattr(app_presence,'_window_reporting',set())
    app_presence.record(42,None,'notepad.exe',windows=None)
    checked=app_presence.refine(result(),42,'agent:remote',None,np.zeros((40,60,3),dtype=np.uint8))
    assert checked.boxes.cls.tolist()==[0,1]


def test_window_coordinates_cover_negative_origin_monitors():
    from workstation.app_presence import normalize
    assert normalize((-1600,100,-800,700),(-1920,0,3840,1080))==[320/3840,100/1080,1120/3840,700/1080]
    assert normalize((2000,100,2400,600),(0,0,1920,1080)) is None

"""The alarm loops locally and remains on during a lost server connection."""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock
import sys
import pytest


def load_agent():
    spec=importlib.util.spec_from_file_location('test_agent',Path(__file__).resolve().parents[2]/'workstation'/'agent.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_siren_is_valid_and_audio_loops_until_stopped(tmp_path,monkeypatch):
    agent=load_agent();sound=MagicMock(SND_FILENAME=1,SND_ASYNC=2,SND_LOOP=4)
    monkeypatch.setitem(sys.modules,'winsound',sound);monkeypatch.setattr(agent.tempfile,'gettempdir',lambda:str(tmp_path))
    player=agent.AlarmPlayer();player.set(True);player.set(True)
    sound.PlaySound.assert_called_once_with(str(player.path),7)
    with agent.wave.open(str(player.path)) as wav:
        assert wav.getnframes()/wav.getframerate()==2
    player.set(False);sound.PlaySound.assert_called_with(None,0)


def test_network_failure_never_silences_active_alarm(monkeypatch):
    agent=load_agent();player=MagicMock();player.active=False;monkeypatch.setattr(agent,'AlarmPlayer',lambda:player)
    monkeypatch.setattr(agent,'foreground_process',lambda:'notepad.exe')
    response=MagicMock();response.__enter__.return_value=response
    monkeypatch.setattr(agent,'urlopen',MagicMock(side_effect=[response,OSError('offline')]))
    monkeypatch.setattr(agent.json,'load',lambda _: {'alarm':True})
    waits=iter([None,KeyboardInterrupt()])
    def sleep(_):
        value=next(waits)
        if value:raise value
    monkeypatch.setattr(agent.time,'sleep',sleep)
    with pytest.raises(KeyboardInterrupt):agent.run_agent({'server_url':'https://school.example','token':'test-only'})
    player.set.assert_called_once_with(True)


def test_cleartext_credentials_are_refused_over_classroom_network():
    agent=load_agent()
    with pytest.raises(ValueError,match='HTTPS'):agent.run_agent({'server_url':'http://10.0.0.1:8080','token':'test-only'})

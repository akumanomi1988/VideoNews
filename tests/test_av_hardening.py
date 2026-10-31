"""Regression tests including real local PCM/FFmpeg; no paid providers."""
import hashlib
import json
import math
import shutil
import subprocess
import wave
import os
from array import array
from pathlib import Path

import pytest

from scripts.audio_engine import export_audio, prepare_loop, probe_audio
from scripts.graphic_timing import bind_timing
from scripts.graphics_engine import GraphicsEngine
from scripts.music_library import MusicLibrary
from scripts.atomic_storage import write_json, process_alive


def tone(path, seconds=3, silent=False):
    with wave.open(str(path),'wb') as out:
        out.setparams((1,2,24000,0,'NONE','not compressed'))
        out.writeframes(array('h',(0 if silent else round(4500*math.sin(2*math.pi*330*i/24000))
                                  for i in range(round(seconds*24000)))).tobytes())


def test_music_revocation_and_modified_bytes_never_reselect(tmp_path):
    tone(tmp_path/'own.wav')
    entry=dict(id='one',name='Original fixture',author='Test author',file='own.wav',duration=3,
        category='Neutral Ambient',intensity=.2,license='Original test fixture only',source='Local test generator',
        attribution='',commercial_use=True,moods=['ambient'])
    catalog=tmp_path/'catalog.json';catalog.write_text(json.dumps([entry]))
    library=MusicLibrary(tmp_path);selection=library.select()
    assert library.verify_selection(selection)==str(tmp_path/'own.wav')
    tone(tmp_path/'own.wav',seconds=2)
    with pytest.raises(ValueError,match='changed'):library.verify_selection(selection)
    entry['commercial_use']=False;catalog.write_text(json.dumps([entry]))
    with pytest.raises(ValueError,match='revoked'):library.verify_selection(selection)


@pytest.mark.parametrize('content',['{}','[null]','[{"id": []}]'])
def test_malformed_catalog_is_a_controlled_error(tmp_path,content):
    (tmp_path/'catalog.json').write_text(content)
    with pytest.raises(ValueError):MusicLibrary(tmp_path).tracks()


def test_graphic_receipt_reuses_valid_and_repairs_corrupt_assets(tmp_path):
    engine=GraphicsEngine(['source'])
    spec={'kind':'fact_card','title':'Verified','items':[{'label':'Source-bound fact','source_url':'source'}]}
    first=engine.render(spec,tmp_path);path=Path(first['png']);stamp=path.stat().st_mtime_ns
    assert engine.render(spec,tmp_path)==first and path.stat().st_mtime_ns==stamp
    path.write_bytes(b'corrupt')
    second=engine.render(spec,tmp_path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==second['sha256']
    receipt=next(tmp_path.glob('*.json'));receipt.write_text('{broken')
    assert engine.render(spec,tmp_path)['sha256']==second['sha256']


def test_animation_requires_actual_scene_word_indices(tmp_path):
    srt=tmp_path/'words.srt';srt.write_text('1\n00:00:00,000 --> 00:00:00,300\nOne\n\n2\n00:00:00,500 --> 00:00:00,800\ntwo\n')
    project={'word_boundaries':str(srt),'storyboard':[{'id':'scene','narration':'One two.'}]}
    spec={'items':[{},{}],'cue_word_indices':[0,1]}
    bound=bind_timing(project,'scene',spec,1.2)
    assert bound['cue_seconds']==[0,.5] and bound['duration']==1.2
    with pytest.raises(ValueError,match='disagree'):
        bind_timing(project,'scene',dict(spec,cue_seconds=[0.,.9]),1.2)


def test_audio_export_cannot_overwrite_original(tmp_path):
    source=tmp_path/'voice.wav';tone(source);before=source.read_bytes()
    with pytest.raises(ValueError,match='immutable'):export_audio(source,source)
    assert source.read_bytes()==before


def test_atomic_json_retries_only_local_replace_and_preserves_previous(tmp_path,monkeypatch):
    import scripts.atomic_storage as storage
    path=tmp_path/'job.json';write_json(path,{'status':'running'})
    original=storage.os.replace;attempts=[]
    def transient(source,target):
        attempts.append(1)
        if len(attempts)<3:raise PermissionError('Controlled sharing conflict')
        original(source,target)
    monkeypatch.setattr(storage.os,'replace',transient)
    write_json(path,{'status':'succeeded'})
    assert len(attempts)==3 and json.loads(path.read_text())['status']=='succeeded'
    assert not list(tmp_path.glob('.write-*'))
    assert process_alive(os.getpid()) and not process_alive(None)


def test_second_studio_does_not_interrupt_live_worker(tmp_path):
    from scripts.studio_mcp import VideoNewsStudio
    studio=VideoNewsStudio(tmp_path)
    job=studio._jobs_dir()/('a'*32+'.json')
    write_json(job,{'job_id':'a'*32,'status':'running','worker_pid':os.getpid()})
    VideoNewsStudio(tmp_path)
    assert json.loads(job.read_text())['status']=='running'
    write_json(job,{'job_id':'a'*32,'status':'running'})
    VideoNewsStudio(tmp_path)
    assert json.loads(job.read_text())['status']=='interrupted'


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='Real FFmpeg required')
def test_real_audio_loop_mixing_and_silence_failure_preserves_output(tmp_path):
    voice=tmp_path/'voice.wav';music=tmp_path/'music.wav';loop=tmp_path/'loop.wav';output=tmp_path/'out.wav'
    tone(voice,4);tone(music,2)
    prepare_loop(music,loop)
    assert abs(probe_audio(loop)[1]-1.5)<.01
    report=export_audio(voice,output,music=loop,equalize=True)
    assert math.isfinite(float(report['input_i']))
    assert probe_audio(output)[0]==24000 and abs(probe_audio(output)[1]-4)<.05
    before=output.read_bytes();tone(voice,1,silent=True)
    with pytest.raises(ValueError,match='silent'):export_audio(voice,output)
    assert output.read_bytes()==before


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='Real FFmpeg required')
def test_real_sidechain_reduces_music_during_speech(tmp_path):
    import numpy as np
    rate=24000
    voice=tmp_path/'voice.wav';music=tmp_path/'bed.wav';mixed=tmp_path/'mixed.wav'
    for path,frequency,gated in [(voice,330,True),(music,880,False)]:
        with wave.open(str(path),'wb') as out:
            out.setparams((1,2,rate,0,'NONE','not compressed'))
            out.writeframes(array('h',(round((9000 if gated else 4000)*math.sin(2*math.pi*frequency*i/rate))
                 if not gated or i<4*rate else 0 for i in range(8*rate))).tobytes())
    export_audio(voice,mixed,music=music,level=.2)
    pcm=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(mixed),'-f','f32le','-ac','1','-ar',str(rate),'-'],
        capture_output=True,check=True).stdout
    samples=np.frombuffer(pcm,dtype='<f4')
    def music_amplitude(start):
        segment=samples[start*rate:(start+1)*rate]
        return abs(np.fft.rfft(segment)[880])
    assert music_amplitude(2)<music_amplitude(5)*.7

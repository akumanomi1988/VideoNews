"""Synthetic technical fixture only: not licensed channel music, never publish."""
import json
import math
import subprocess
import wave
from array import array
from pathlib import Path
import numpy as np
from scripts.audio_engine import prepare_loop, export_audio, probe_audio


def pcm(path):
    raw=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(path),'-f','f32le','-ac','1','-ar','24000','-'],
                       capture_output=True,check=True).stdout
    return np.frombuffer(raw,dtype='<f4')


def main():
    root=Path('output/av_upgrade/music_fixture');root.mkdir(parents=True,exist_ok=True)
    for name,freq,gated,duration in [('voice.wav',330,True,8),('music.wav',880,False,2)]:
        with wave.open(str(root/name),'wb') as out:
            out.setparams((1,2,24000,0,'NONE','not compressed'))
            out.writeframes(array('h',(round((9000 if gated else 4000)*math.sin(2*math.pi*freq*i/24000))
                if not gated or i<4*24000 else 0 for i in range(duration*24000))).tobytes())
    loop=prepare_loop(root/'music.wav',root/'loop.wav')
    measurements=export_audio(root/'voice.wav',root/'mix.wav',music=loop,level=.2)
    samples=pcm(root/'mix.wav');unit=pcm(loop)
    spectrum=lambda start:abs(np.fft.rfft(samples[start*24000:(start+1)*24000])[880])
    ratio=float(spectrum(2)/spectrum(5))
    boundary=float(abs(unit[-1]-unit[0]));ordinary=float(np.max(np.abs(np.diff(unit))))
    assert ratio<.7 and boundary<=ordinary*1.5
    assert abs(probe_audio(root/'mix.wav')[1]-8)<.02
    report={'publication_allowed':False,'fixture':'Synthetic tones, not channel music',
        'music_amplitude_speech_to_silence_ratio':ratio,'loop_join_step':boundary,
        'maximum_internal_sample_step':ordinary,'duration_seconds':probe_audio(root/'mix.wav')[1],
        'normalization_measurement':measurements}
    (root/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (root/'NOT_FOR_PUBLICATION.txt').write_text('Synthetic engineering fixture. Never publish as NewSphere music.',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()

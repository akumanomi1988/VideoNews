"""Moderate speech processing and measured, sidechain-controlled local mixing."""
import json
import subprocess
import math
from pathlib import Path
import tempfile
import os


def voice_filter(highpass=False, equalize=False, compress=False):
    chain = []
    if highpass:
        chain.append('highpass=f=65')
    if equalize:
        chain.append('equalizer=f=2500:t=q:w=1:g=1')
    if compress:
        chain.append('acompressor=threshold=0.18:ratio=1.5:attack=20:release=180:makeup=1')
    return ','.join(chain + ['alimiter=limit=0.95:level=false:latency=true'])


def probe_audio(source):
    probe = subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_entries',
        'stream=sample_rate:format=duration','-of','json',str(source)],capture_output=True,
        text=True,check=True,stdin=subprocess.DEVNULL,timeout=30)
    data=json.loads(probe.stdout)
    return int(data['streams'][0]['sample_rate']), float(data['format']['duration'])


def prepare_loop(source, output, crossfade=.5):
    """Build a circular crossfade unit; the join retains waveform continuity."""
    rate,duration=probe_audio(source)
    if not math.isfinite(crossfade) or not .05<=crossfade<=min(2,duration/3):
        raise ValueError('Music must be long enough for the configured crossfade')
    graph=(f'[0:a]asplit=3[a][b][c];[a]atrim=start={crossfade}:end={duration-crossfade},asetpts=PTS-STARTPTS[mid];'
           f'[b]atrim=start={duration-crossfade},asetpts=PTS-STARTPTS[tail];'
           f'[c]atrim=end={crossfade},asetpts=PTS-STARTPTS[head];'
           f'[tail][head]acrossfade=d={crossfade}:c1=tri:c2=tri[join];[mid][join]concat=n=2:v=0:a=1[out]')
    subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-i',str(source),'-filter_complex',graph,
        '-map','[out]','-ar',str(rate),'-c:a','pcm_s24le',str(output)],check=True,
        capture_output=True,stdin=subprocess.DEVNULL,timeout=120)
    return output


def export_audio(source, output, music=None, level=.12, ducking=6, **processing):
    if Path(output).suffix.lower() != '.wav' or Path(source).resolve()==Path(output).resolve():
        raise ValueError('Export requires a separate WAV path; original narration is immutable')
    if not 0 <= level <= .3 or not 2 <= ducking <= 12:
        raise ValueError('Invalid music level or ducking ratio')
    rate,duration=probe_audio(source)
    command = ['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', str(source)]
    filters = f'[0:a]{voice_filter(**processing)}[v];'
    if music:
        command += ['-stream_loop', '-1', '-i', str(music)]
        filters += (f'[v]asplit=2[voice][key];[1:a]volume={level},afade=t=in:d=1,afade=t=out:st={max(0,duration-1)}:d=1[bg];'
                    f'[bg][key]sidechaincompress=threshold=0.025:ratio={ducking}:attack=15:release=350[duck];'
                    '[voice][duck]amix=inputs=2:duration=first:normalize=0[m];')
        label = 'm'
    else:
        label = 'v'
    # Measure first, then apply the measured normalization rather than guessing gain.
    measurement_command = list(command)
    measurement_command[measurement_command.index('error')] = 'info'
    measure = subprocess.run(measurement_command + ['-filter_complex', filters + f'[{label}]loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json',
        '-f', 'null', '-'], capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True, timeout=900)
    data, _ = json.JSONDecoder().raw_decode(measure.stderr[measure.stderr.rfind('{'):])
    if any(not math.isfinite(float(data[k])) for k in ('input_i','input_tp','input_lra','input_thresh','target_offset')):
        raise ValueError('Audio is silent or cannot be normalized reliably')
    norm = ('loudnorm=I=-16:TP=-1.5:LRA=7:linear=true:'
            f"measured_I={data['input_i']}:measured_TP={data['input_tp']}:"
            f"measured_LRA={data['input_lra']}:measured_thresh={data['input_thresh']}:offset={data['target_offset']}")
    # Restore the source rate after loudnorm's internal oversampling; keep original PCM fidelity.
    output=Path(output)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        staged=Path(temp)/'audio.wav'
        subprocess.run(command + ['-filter_complex',filters+f'[{label}]{norm}[out]', '-map','[out]',
            '-ar',str(rate),'-c:a','pcm_s24le',str(staged)],capture_output=True,stdin=subprocess.DEVNULL,check=True,timeout=900)
        os.replace(staged,output)
    return data

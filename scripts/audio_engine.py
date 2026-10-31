"""Moderate speech processing and measured, sidechain-controlled local mixing."""
import json
import subprocess


def voice_filter(highpass=False, equalize=False, compress=False):
    chain = []
    if highpass:
        chain.append('highpass=f=65')
    if equalize:
        chain.append('equalizer=f=2500:t=q:w=1:g=1')
    if compress:
        chain.append('acompressor=threshold=0.18:ratio=1.5:attack=20:release=180:makeup=1')
    return ','.join(chain + ['alimiter=limit=0.95:level=false'])


def export_audio(source, output, music=None, level=.12, ducking=6, **processing):
    if not 0 <= level <= .3 or not 2 <= ducking <= 12:
        raise ValueError('Invalid music level or ducking ratio')
    command = ['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', str(source)]
    filters = f'[0:a]{voice_filter(**processing)}[v];'
    if music:
        command += ['-stream_loop', '-1', '-i', str(music)]
        filters += (f'[v]asplit=2[voice][key];[1:a]volume={level},afade=t=in:d=1[bg];'
                    f'[bg][key]sidechaincompress=threshold=0.025:ratio={ducking}:attack=15:release=350[duck];'
                    '[voice][duck]amix=inputs=2:duration=first:normalize=0[m];')
        label = 'm'
    else:
        label = 'v'
    # Measure first, then apply the measured normalization rather than guessing gain.
    measurement_command = list(command)
    measurement_command[measurement_command.index('error')] = 'info'
    measure = subprocess.run(measurement_command + ['-filter_complex', filters + f'[{label}]loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json',
        '-f', 'null', '-'], capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True)
    data, _ = json.JSONDecoder().raw_decode(measure.stderr[measure.stderr.rfind('{'):])
    norm = ('loudnorm=I=-16:TP=-1.5:LRA=7:linear=true:'
            f"measured_I={data['input_i']}:measured_TP={data['input_tp']}:"
            f"measured_LRA={data['input_lra']}:measured_thresh={data['input_thresh']}:offset={data['target_offset']}")
    # Restore the source rate after loudnorm's internal oversampling; keep original PCM fidelity.
    probe = subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=sample_rate',
        '-of','csv=p=0',str(source)],capture_output=True,text=True,check=True)
    subprocess.run(command + ['-filter_complex',filters+f'[{label}]{norm}[out]', '-map','[out]',
        '-ar',probe.stdout.strip(),'-c:a','pcm_s24le',str(output)],capture_output=True,stdin=subprocess.DEVNULL,check=True)
    return data

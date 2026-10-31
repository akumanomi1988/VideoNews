"""Reproducible local Lucy excerpt; never edits the published project or uploads."""
import json
import subprocess
from pathlib import Path
from scripts.audio_engine import export_audio
from scripts.graphics_engine import GraphicsEngine


def main():
    root=Path('output/av_upgrade');root.mkdir(exist_ok=True)
    original=Path('output/studio/a32e5c2505fc454d96c3f734f3b3a469')
    project=json.loads((original/'project.json').read_text(encoding='utf-8'))
    for name,source,options in [('A_original',original/'narration.wav',{}),
        ('B_mp3',original/'narration.mp3',{}),('C_processed',original/'narration.wav',{'highpass':True,'equalize':True})]:
        report=export_audio(source,root/(name+'.wav'),**options)
        (root/(name+'.json')).write_text(json.dumps(report,indent=2))
    source=project['sources'][0]['url']; engine=GraphicsEngine([source]);clips=[]
    for index,(kind,title,labels) in enumerate([
        ('timeline','Lucy: etapas del viaje',['2021: lanzamiento','2026: región troyana','2027: primer sobrevuelo previsto']),
        ('process_diagram','El destino de Lucy',['Órbita alrededor del Sol','Dos grupos troyanos','Explorar ambos grupos']),
        ('fact_card','Rocas muy separadas',['Regiones orbitales estables','Más de nueve millones de km de separación media','Los objetivos aparecen como puntos'])]):
        spec={'kind':kind,'title':title,'items':[{'label':x,'source_url':source} for x in labels],
              'duration':20.,'animation':'reveal' if index<2 else 'none','cue_seconds':[0.,6.,12.] if index<2 else []}
        result=engine.render(spec,root/'graphics')
        clip=root/f'clip{index}.mp4'
        if 'animation' in result:
            clips.append(Path(result['animation']).resolve())
        else:
            subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-loop','1','-i',result['png'],'-t','20',
                '-r','24','-c:v','libx264','-pix_fmt','yuv420p',str(clip)],check=True)
            clips.append(clip.resolve())
    listing=root/'concat.txt';listing.write_text('\n'.join("file '"+str(p).replace('\\','/')+"'" for p in clips))
    subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','0','-i',str(listing),
        '-i',str(root/'C_processed.wav'),'-t','60','-vf',"subtitles=output/av_upgrade/subtitles.srt",
        '-c:v','libx264','-preset','veryfast','-c:a','aac','-b:a','320k','-movflags','+faststart',str(root/'demo.mp4')],check=True)


if __name__=='__main__':
    import shutil
    Path('output/av_upgrade').mkdir(exist_ok=True)
    shutil.copy2('output/studio/a32e5c2505fc454d96c3f734f3b3a469/subtitles.srt','output/av_upgrade/subtitles.srt')
    main()

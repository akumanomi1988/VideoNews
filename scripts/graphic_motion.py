"""FFmpeg motion from reusable layers: one PNG per element, not one per frame."""
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from scripts.graphic_layouts import boxes,item,connections


def render(engine,spec,folder,digest,font):
    w,h=(1920,1080) if spec.aspect_ratio=='16:9' else (1080,1920)
    base=Path(folder)/(digest+'-base.png');engine.draw(spec,base,time=-1)
    positions=boxes(spec,w,h)
    command=['ffmpeg','-nostdin','-y','-v','error','-loop','1','-framerate','24','-i',str(base)]
    filters=[];current='0:v'
    for i,box in enumerate(positions):
        layer=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(layer)
        item(draw,spec,i,box,font)
        # Connections emerge with their target rather than revealing future relationships.
        if spec.kind in ('timeline','process_diagram') and i:
            edge=spec.model_copy(update={'relations':[{'source':i-1,'target':i,'label':''}],'kind':'flow_diagram'})
            connections(draw,edge,positions,font)
        elif spec.relations:
            edge=spec.model_copy(update={'relations':[r for r in spec.relations if r['target']==i]})
            connections(draw,edge,positions,font)
        path=Path(folder)/(digest+f'-layer-{i}.png');layer.save(path)
        command+=['-loop','1','-framerate','24','-i',str(path)]
        cue=spec.cue_seconds[i];next_cue=spec.cue_seconds[i+1] if i+1<len(positions) else spec.duration
        effect_duration=min(.7,next_cue-cue,spec.duration-cue)
        if effect_duration<=0:raise ValueError('Animation event has no time before the next cue')
        label=f'layer{i}';x,y,bw,bh=box
        effect=f'[{i+1}:v]format=rgba'
        if spec.animation=='highlight':
            effect+=f",drawbox=x={x}:y={y}:w={bw}:h={bh}:color=yellow:t=4:enable='between(t,{cue},{next_cue})'"
        elif spec.animation in ('bars','path','timeline'):
            axis='Y' if h>w and spec.animation!='bars' else 'X'
            start=y if axis=='Y' else x
            span=bh if axis=='Y' else bw
            if spec.animation in ('path','timeline'):
                # Begin at the visible path/node, not the canvas origin: a
                # canvas-wide mask would add an unintended spatial delay.
                incoming=[r for r in spec.relations if r['target']==i]
                if spec.kind in ('timeline','process_diagram') and i:
                    incoming=[{'source':i-1,'target':i}]
                if incoming:
                    source=positions[incoming[0]['source']]
                    origin=source[1]+source[3] if axis=='Y' else source[0]+source[2]
                    start=min(start,origin)
                    span=(y+bh if axis=='Y' else x+bw)-start
            boundary=f'{start}+{span}*min(1,max(0,(T-{cue})/{effect_duration}))'
            # Compute only one grayscale mask plane, not three unchanged RGB
            # planes per pixel. Preserve the original transparent layer alpha.
            filters.append(f"color=white:s={w}x{h}:r=24,format=gray,geq=lum='if(lte({axis},{boundary}),255,0)'[mask{i}]")
            filters.append(f'[{i+1}:v]format=rgba,split[image{i}][extract{i}]')
            filters.append(f'[extract{i}]alphaextract[alpha{i}]')
            filters.append(f'[alpha{i}][mask{i}]blend=all_mode=multiply[mergedalpha{i}]')
            effect=f'[image{i}][mergedalpha{i}]alphamerge'
        effect+=f'[{label}]';filters.append(effect)
        move=f"-80*(1-min(1,max(0,(t-{cue})/{effect_duration})))" if spec.animation=='move' else '0'
        enabled=f"gte(t,{cue})"
        if spec.animation=='before_after' and i<len(positions)-1:
            enabled+=f'*lt(t,{next_cue})'
        filters.append(f"[{current}][{label}]overlay=x='{move}':y=0:enable='{enabled}':shortest=1[out{i}]")
        current=f'out{i}'
    video=Path(folder)/(digest+'.mp4')
    command+=['-filter_complex',';'.join(filters),'-map',f'[{current}]','-t',str(spec.duration),'-r','24',
              '-c:v','libx264','-pix_fmt','yuv420p','-preset','veryfast',str(video)]
    subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,check=True,timeout=600)
    return video

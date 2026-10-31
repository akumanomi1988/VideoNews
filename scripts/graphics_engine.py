"""Source-bound NewSphere graphics and local progressive motion, without an LLM."""
import hashlib
import json
import subprocess
import tempfile
import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from functools import lru_cache


@lru_cache(maxsize=24)
def _font(size):
    return ImageFont.truetype('C:/Windows/Fonts/arial.ttf', size)


class Datum(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    label: str = Field(min_length=1, max_length=70)
    value: float | None = Field(default=None, allow_inf_nan=False)
    source_url: str


class GraphicSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['timeline','comparison','statistical_chart','process_diagram','flow_diagram',
                  'fact_card','scientific_schematic','geographic_map']
    title: str = Field(min_length=1, max_length=65)
    aspect_ratio: Literal['16:9','9:16'] = '16:9'
    items: list[Datum] = Field(min_length=1,max_length=6)
    unit: str = Field(default='',max_length=25)
    animation: Literal['none','reveal','bars','highlight'] = 'none'
    cue_seconds: list[float] = Field(default_factory=list)
    cue_word_indices: list[int] = Field(default_factory=list)
    duration: float = Field(default=8.,ge=1,le=120)
    geometry: dict | None = None
    geometry_source: str = ''


class GraphicsEngine:
    def __init__(self, registered_sources):
        self.sources = set(registered_sources)

    def validate(self, data):
        spec = GraphicSpec.model_validate(data)
        if not math.isfinite(spec.duration) or any(not math.isfinite(t) for t in spec.cue_seconds):
            raise ValueError('Durations and cues must be finite')
        if spec.animation == 'bars' and spec.kind != 'statistical_chart':
            raise ValueError('Bar animation requires a statistical chart')
        if any(x.source_url not in self.sources for x in spec.items):
            raise ValueError('Every datum must reference a registered project source')
        if spec.kind == 'geographic_map':
            if spec.geometry_source not in self.sources or not spec.geometry or spec.geometry.get('type')!='Polygon':
                raise ValueError('Maps require source-bound GeoJSON Polygon geometry')
            rings=spec.geometry.get('coordinates',[])
            if len(rings)!=1 or not 4<=len(rings[0])<=10000 or rings[0][0]!=rings[0][-1]:
                raise ValueError('Provide one closed exterior polygon; holes and multipolygons are unsupported')
            if any(len(p)!=2 or not all(type(v) in (float,int) for v in p) or not -180<=p[0]<=180 or not -90<=p[1]<=90 for p in rings[0]):
                raise ValueError('Invalid longitude/latitude geometry')
            if max(p[0] for p in rings[0])-min(p[0] for p in rings[0])>180:
                raise ValueError('Antimeridian-crossing geometry requires a different projection')
        if spec.kind == 'statistical_chart' and (not spec.unit or any(x.value is None or x.value < 0 for x in spec.items)):
            raise ValueError('Charts require a unit and nonnegative sourced values')
        if spec.animation != 'none' and (len(spec.cue_seconds)!=len(spec.items) or
            spec.cue_seconds != sorted(set(spec.cue_seconds)) or any(t<0 or t>=spec.duration for t in spec.cue_seconds)):
            raise ValueError('Animation requires ordered narration-relative cues for every item')
        return spec

    def draw(self, spec, output, time=None):
        spec = self.validate(spec) if isinstance(spec,dict) else spec
        w,h = (1920,1080) if spec.aspect_ratio=='16:9' else (1080,1920)
        im=Image.new('RGB',(w,h),(7,20,34)); d=ImageDraw.Draw(im)
        font=_font
        margin=int(w*.075); title_font=font(55 if w>h else 45)
        if d.textbbox((0,0),spec.title,font=title_font)[2] > w-2*margin:
            raise ValueError('Title exceeds safe width; shorten it')
        d.text((margin,int(h*.07)),'NEWSPHERE',font=font(28),fill='#22d4df')
        d.text((margin,int(h*.13)),spec.title,font=title_font,fill='white')
        y0=int(h*.28); step=int(h*.47/len(spec.items)); size=min(40,int(step*.45))
        if spec.kind=='geographic_map':
            points=spec.geometry['coordinates'][0]
            xs=[p[0] for p in points];ys=[p[1] for p in points]
            if max(xs)==min(xs) or max(ys)==min(ys):raise ValueError('Degenerate map geometry')
            scale=min((w*.35)/(max(xs)-min(xs)),(h*.4)/(max(ys)-min(ys)))
            polygon=[(int(w*.57+(x-min(xs))*scale),int(h*.7-(y-min(ys))*scale)) for x,y in points]
            d.polygon(polygon,fill='#144957',outline='#22d4df',width=4)
        maximum=max([x.value or 0 for x in spec.items]+[1])
        for i,item in enumerate(spec.items):
            cue=spec.cue_seconds[i] if spec.cue_seconds else 0
            if time is not None and time<cue: continue
            y=y0+i*step
            available = w*.42 if spec.kind=='geographic_map' else w-2*margin-(250 if spec.kind=='statistical_chart' else 50)
            if d.textbbox((0,0),item.label,font=font(size))[2]>available:
                raise ValueError('Label exceeds safe width; shorten it')
            color='#ffbd65' if spec.animation=='highlight' and time is not None and cue<=time<cue+1 else '#22d4df'
            d.ellipse((margin,y+8,margin+16,y+24),fill=color)
            d.text((margin+35,y),item.label,font=font(size),fill='white')
            if spec.kind=='statistical_chart':
                progress=min(1,max(0,(time-cue)/.7)) if time is not None else 1
                length=int((w-2*margin)*.65*(item.value/maximum)*progress)
                d.rectangle((margin+35,y+size+5,margin+35+max(1,length),y+size+17),fill=color)
                d.text((w-margin-180,y),f'{item.value:g} {spec.unit}',font=font(28),fill='white')
            elif spec.kind in ('process_diagram','flow_diagram','timeline') and i<len(spec.items)-1:
                d.line((margin+8,y+28,margin+8,y+step),fill=color,width=3)
        d.text((margin,int(h*.81)),'Fuentes registradas en el proyecto · Gráfico explicativo',font=font(23),fill='#9bb9c6')
        im.save(output)
        return output

    def render(self,data,folder):
        spec=self.validate(data);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256(spec.model_dump_json().encode()).hexdigest()[:16]
        receipt=folder/(digest+'.json')
        if receipt.is_file():
            try:
                cached=json.loads(receipt.read_text(encoding='utf-8'))
            except (ValueError,OSError):
                cached={}
            if not isinstance(cached,dict) or not all(isinstance(cached.get(k),str) for k in ('png','sha256')):
                cached={}
            if (cached.get('spec') == spec.model_dump() and
                Path(cached['png']).is_file() and hashlib.sha256(Path(cached['png']).read_bytes()).hexdigest()==cached['sha256'] and
                (not cached.get('animation') or Path(cached['animation']).is_file() and
                 hashlib.sha256(Path(cached['animation']).read_bytes()).hexdigest()==cached.get('animation_sha256'))):
                return cached
        png=folder/(digest+'.png');self.draw(spec,png)
        result={'png':str(png),'sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'spec':spec.model_dump(),'provider':'NewSphere GraphicsEngine'}
        if spec.animation!='none':
            video=folder/(digest+'.mp4')
            with tempfile.TemporaryDirectory(dir=folder) as tmp:
                for frame in range(round(spec.duration*24)):
                    self.draw(spec,Path(tmp)/f'{frame:05}.png',frame/24)
                subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-framerate','24','-i',str(Path(tmp)/'%05d.png'),
                    '-c:v','libx264','-pix_fmt','yuv420p','-preset','veryfast',str(video)],stdin=subprocess.DEVNULL,check=True,timeout=600)
            result['animation']=str(video)
            result['animation_sha256']=hashlib.sha256(video.read_bytes()).hexdigest()
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=folder,suffix='.json.tmp',delete=False) as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
            temporary=stream.name
        os.replace(temporary,receipt)
        return result

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
    animation: Literal['none','reveal','bars','highlight','timeline','path','move','before_after'] = 'none'
    cue_seconds: list[float] = Field(default_factory=list)
    cue_word_indices: list[int] = Field(default_factory=list)
    duration: float = Field(default=8.,ge=1,le=120)
    geometry: dict | None = None
    geometry_source: str = ''
    geometry_id: str = ''
    relations: list[dict] = Field(default_factory=list,max_length=12)
    cue_phrases: list[str] = Field(default_factory=list)
    cue_occurrences: list[int] = Field(default_factory=list)


class GraphicsEngine:
    def __init__(self, registered_sources):
        self.sources = set(registered_sources)

    def validate(self, data):
        spec = GraphicSpec.model_validate(data)
        if not math.isfinite(spec.duration) or any(not math.isfinite(t) for t in spec.cue_seconds):
            raise ValueError('Durations and cues must be finite')
        if spec.animation == 'bars' and spec.kind != 'statistical_chart':
            raise ValueError('Bar animation requires a statistical chart')
        if spec.animation=='before_after' and (spec.kind!='comparison' or len(spec.items)!=2):
            raise ValueError('Before/after requires a comparison with exactly two states')
        if spec.animation=='timeline' and spec.kind!='timeline':
            raise ValueError('Timeline progression requires a timeline layout')
        if spec.animation=='path' and spec.kind not in ('timeline','process_diagram','flow_diagram','scientific_schematic'):
            raise ValueError('Path drawing requires a connected diagram or timeline')
        if any(x.source_url not in self.sources for x in spec.items):
            raise ValueError('Every datum must reference a registered project source')
        for relation in spec.relations:
            if (set(relation)!={'source','target','label'} or
                any(type(relation[k])!=int or not 0<=relation[k]<len(spec.items) for k in ('source','target')) or
                relation['source']==relation['target'] or not isinstance(relation['label'],str) or len(relation['label'])>30):
                raise ValueError('Relations require valid distinct item indices and a short label')
        if spec.kind in ('scientific_schematic','flow_diagram') and len(spec.items)>1 and not spec.relations:
            raise ValueError('Scientific and flow diagrams require explicit source-supported relationships')
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
        from scripts.graphic_layouts import boxes, item, connections
        positions=boxes(spec,w,h)
        for i,box in enumerate(positions):
            cue=spec.cue_seconds[i] if spec.cue_seconds else 0
            if time is None or time>=cue:item(d,spec,i,box,font)
        # Draw relationship labels last so node fills cannot cover their text.
        if time is None:connections(d,spec,positions,font)
        caption='Proyección equirectangular · Geometría de fuente registrada' if spec.kind=='geographic_map' else 'Fuentes registradas en el proyecto · Gráfico explicativo'
        d.text((margin,int(h*.81)),caption,font=font(23),fill='#9bb9c6')
        im.save(output)
        return output

    def render(self,data,folder):
        spec=self.validate(data);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        version='layout-v3-motion-v2-stat-scale-v2:' if spec.kind=='statistical_chart' else 'layout-v3-motion-v2:'
        digest=hashlib.sha256((version+spec.model_dump_json()).encode()).hexdigest()[:16]
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
                if cached.get('static_layout_revision')!=4:
                    self.draw(spec,cached['png'])
                    cached['sha256']=hashlib.sha256(Path(cached['png']).read_bytes()).hexdigest()
                    cached['static_layout_revision']=4
                    from scripts.atomic_storage import write_json
                    write_json(receipt,cached)
                return cached
        png=folder/(digest+'.png');self.draw(spec,png)
        result={'png':str(png),'sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'spec':spec.model_dump(),'provider':'NewSphere GraphicsEngine','static_layout_revision':4}
        if spec.animation!='none':
            from scripts.graphic_motion import render
            video=render(self,spec,folder,digest,_font)
            result['animation']=str(video)
            result['animation_sha256']=hashlib.sha256(video.read_bytes()).hexdigest()
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=folder,suffix='.json.tmp',delete=False) as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
            temporary=stream.name
        os.replace(temporary,receipt)
        return result

import json
import shutil
import pytest
from scripts.graphic_timing import bind_timing
from scripts.graphics_engine import GraphicsEngine
from scripts.production_audio import AudioSettings


def project_words(tmp_path):
    path=tmp_path/'words.srt'
    words=['La','sonda','mira','la','sonda','viaja']
    path.write_text('\n'.join(f'{i+1}\n00:00:0{i},000 --> 00:00:0{i},500\n{w}\n' for i,w in enumerate(words)))
    return {'word_boundaries':str(path),'storyboard':[{'id':'a','narration':'La sonda mira la sonda viaja.'}]}


def test_phrase_resolution_repetition_missing_and_order(tmp_path):
    p=project_words(tmp_path);base={'items':[{},{}],'cue_phrases':['la sonda','viaja']}
    with pytest.raises(ValueError,match='Ambiguous'):bind_timing(p,'a',base,6)
    bound=bind_timing(p,'a',dict(base,cue_occurrences=[2,1]),6)
    assert bound['cue_seconds']==[3.,5.] and bound['cue_word_indices']==[3,5]
    with pytest.raises(ValueError,match='Unresolved'):
        bind_timing(p,'a',dict(base,cue_phrases=['missing','viaja']),6)
    with pytest.raises(ValueError):
        bind_timing(p,'a',dict(base,cue_phrases=['viaja','mira']),6)


def test_settings_reject_unknown_and_unsafe_audio():
    with pytest.raises(ValueError):AudioSettings.model_validate({'bitrate_kbps':999})
    with pytest.raises(ValueError):AudioSettings.model_validate({'unknown':True})


def test_attribution_is_idempotent_and_never_truncated():
    from scripts.music_credit import apply_credit
    credited=apply_credit('Source-backed description','Artist — license terms')
    assert apply_credit(credited,'Artist — license terms')==credited
    assert 'Artist' not in apply_credit(credited,'')
    with pytest.raises(ValueError):apply_credit('x'*4990,'Mandatory attribution must be preserved')


def test_layout_families_have_distinct_pixels(tmp_path):
    from pathlib import Path
    import hashlib
    hashes=[]
    for kind in ['timeline','comparison','statistical_chart','process_diagram','flow_diagram','fact_card','scientific_schematic']:
        spec={'kind':kind,'title':'Same content','unit':'km','items':[{'label':'One','source_url':'s','value':2.},
              {'label':'Two','source_url':'s','value':3.}]}
        if kind in ('flow_diagram','scientific_schematic'):spec['relations']=[{'source':1,'target':0,'label':'relationship'}]
        result=GraphicsEngine(['s']).render(spec,tmp_path/kind)
        hashes.append(hashlib.sha256(Path(result['png']).read_bytes()).hexdigest())
    assert len(set(hashes))==7


def test_small_scientific_values_preserve_bar_proportions(tmp_path):
    from PIL import Image
    from scripts.graphic_layouts import boxes
    from scripts.graphics_engine import GraphicSpec
    base={'kind':'statistical_chart','title':'Scale accuracy','unit':'units','items':[
        {'label':'One','source_url':'s','value':1.},{'label':'Two','source_url':'s','value':2.}]}
    small=dict(base,items=[dict(item,value=item['value']*1e-15) for item in base['items']])
    a=GraphicsEngine(['s']).render(base,tmp_path/'normal');b=GraphicsEngine(['s']).render(small,tmp_path/'small')
    x,y,w,h=boxes(GraphicSpec.model_validate(base),1920,1080)[0]
    region=(x+18,y+50,x+w-202,y+70)
    assert Image.open(a['png']).crop(region).tobytes()==Image.open(b['png']).crop(region).tobytes()


def test_native_graphic_repair_idempotency_and_published_guard(tmp_path):
    from pathlib import Path
    from scripts.studio_mcp import VideoNewsStudio,StudioError
    studio=VideoNewsStudio(tmp_path);project=studio.create_project('Graphic recovery acceptance','short');pid=project['id']
    studio.save_sources(pid,[{'title':'Source','url':'https://example.org/fact','publisher':'Fixture','published_at':'','summary':'Original controlled fixture'}])
    studio.save_storyboard(pid,[{'id':'a','narration':'Known text.','visual_prompt':'Original source bound diagram','visual_type':'graphic'}])
    spec={'kind':'fact_card','title':'Fact','aspect_ratio':'9:16','items':[{'label':'Known fact','source_url':'https://example.org/fact'}]}
    first=studio.generate_graphic(pid,'a',spec)
    assert studio.generate_graphic(pid,'a',spec)['asset']['id']==first['asset']['id']
    Path(first['asset']['path']).write_bytes(b'corrupted import')
    repaired=studio.generate_graphic(pid,'a',spec)
    assert len(studio.get_project(pid)['asset_records'])==1 and repaired['asset']['id']!=first['asset']['id']
    p=studio._read(pid);p['status']='published';studio._save(p)
    with pytest.raises(StudioError):studio.generate_graphic(pid,'a',spec)


def test_native_maps_require_imported_geometry(tmp_path):
    from pathlib import Path
    from scripts.studio_mcp import VideoNewsStudio,StudioError
    studio=VideoNewsStudio(tmp_path);pid=studio.create_project('Map contract fixture','short')['id']
    url='https://example.org/controlled-geometry'
    studio.save_sources(pid,[{'title':'Fixture dataset','url':url,'publisher':'Test fixture','published_at':'','summary':'Synthetic unit-test coordinates, never news data'}])
    studio.save_storyboard(pid,[{'id':'map','narration':'Fixture text','visual_prompt':'Fixture polygon map'}])
    polygon={'type':'Polygon','coordinates':[[[0.,0.],[1.,0.],[1.,1.],[0.,0.]]]}
    spec={'kind':'geographic_map','title':'Test geometry','aspect_ratio':'9:16','items':[{'label':'Test only','source_url':url}],
          'geometry':polygon,'geometry_source':url}
    with pytest.raises(StudioError,match='geometry_id'):studio.generate_graphic(pid,'map',spec)
    (studio.workspace/'_imports'/'test.geojson').write_text(json.dumps(polygon))
    record=studio.import_geometry(pid,'test.geojson',url)
    result=studio.generate_graphic(pid,'map',dict(spec,geometry_id=record['id']))
    assert Path(result['png']).is_file()


@pytest.mark.parametrize('kind',['timeline','comparison','statistical_chart','process_diagram','flow_diagram','fact_card','scientific_schematic','geographic_map'])
def test_layouts_have_distinct_source_bound_receipts(tmp_path,kind):
    spec={'kind':kind,'title':'Example','unit':'km','items':[{'label':'One','source_url':'s','value':2.},
          {'label':'Two','source_url':'s','value':3.}]}
    if kind in ('flow_diagram','scientific_schematic'):spec['relations']=[{'source':0,'target':1,'label':'test relation'}]
    if kind=='geographic_map':spec.update(geometry={'type':'Polygon','coordinates':[[[0.,0.],[1.,0.],[1.,1.],[0.,0.]]]},geometry_source='s')
    result=GraphicsEngine(['s']).render(spec,tmp_path)
    assert result['sha256'] and result['spec']['kind']==kind


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='Real FFmpeg')
@pytest.mark.parametrize('animation,ratio',[(a,'16:9') for a in ['reveal','bars','highlight','timeline','path','move','before_after']]+[('path','9:16')])
def test_real_motion_primitives_decode(tmp_path,animation,ratio):
    import subprocess
    kind='statistical_chart' if animation=='bars' else 'comparison' if animation=='before_after' else 'timeline'
    spec={'kind':kind,'title':'Motion fixture','unit':'km','duration':1.,'animation':animation,'aspect_ratio':ratio,
          'cue_seconds':[0.,.5],'items':[{'label':'One','source_url':'s','value':2.},{'label':'Two','source_url':'s','value':3.}]}
    result=GraphicsEngine(['s']).render(spec,tmp_path)
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',result['animation'],'-f','null','-'],
                   capture_output=True,check=True,timeout=60)
    assert len(list(tmp_path.glob('*layer*.png')))==2
    frames=[]
    for at in ('0.1','0.8'):
        frames.append(subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',at,'-i',result['animation'],
            '-frames:v','1','-vf','scale=320:180','-f','rawvideo','-pix_fmt','rgb24','-'],
            capture_output=True,check=True,timeout=30).stdout)
    assert frames[0]!=frames[1],'Motion must change actual decoded pixels'

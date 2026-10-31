import pytest
from scripts.graphics_engine import GraphicsEngine
from scripts.music_library import MusicLibrary

@pytest.mark.parametrize('kind',['timeline','comparison','statistical_chart','process_diagram','flow_diagram','fact_card','scientific_schematic'])
@pytest.mark.parametrize('ratio',['16:9','9:16'])
def test_graphics_source_bound_render(tmp_path,kind,ratio):
    from PIL import Image
    spec={'kind':kind,'title':'Verified fact','aspect_ratio':ratio,'unit':'km',
          'items':[{'label':'Observation','value':12.,'source_url':'https://example.org/source'}]}
    result=GraphicsEngine(['https://example.org/source']).render(spec,tmp_path)
    with Image.open(result['png']) as im:assert im.size==((1920,1080) if ratio=='16:9' else (1080,1920))

def test_unknown_source_and_map_are_blocked():
    engine=GraphicsEngine([])
    with pytest.raises(ValueError):engine.validate({'kind':'fact_card','title':'Unsupported','items':[{'label':'Claim','source_url':'https://unverified.test'}]})
    with pytest.raises(ValueError):engine.validate({'kind':'geographic_map','title':'Map','items':[{'label':'Place','source_url':'x'}]})

def test_no_licensed_music_does_not_substitute(tmp_path):
    assert MusicLibrary(tmp_path).select()['track'] is None
    assert MusicLibrary(tmp_path).select('none')['track'] is None

def test_invalid_animation_cues_are_rejected():
    with pytest.raises(ValueError):GraphicsEngine(['x']).validate({'kind':'fact_card','title':'Fact','animation':'reveal',
        'cue_seconds':[5.,1.],'items':[{'label':'One','source_url':'x'},{'label':'Two','source_url':'x'}]})

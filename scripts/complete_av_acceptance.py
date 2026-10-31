"""Five-layout, phrase-anchored acceptance through the normal Studio renderer."""
import copy
import json
import shutil
from pathlib import Path
from scripts.studio_mcp import VideoNewsStudio
from scripts.atomic_storage import write_json


def main():
    studio=VideoNewsStudio();source=studio.get_project('a32e5c2505fc454d96c3f734f3b3a469')
    before=studio._hash(Path(source['video']))
    marker=Path('output/av_upgrade/complete_acceptance.json')
    fresh=(studio.get_project(json.loads(marker.read_text(encoding='utf-8'))['project_id']) if marker.is_file()
           else studio.create_project('Complete audiovisual local acceptance','long'))
    studio._require_editable(fresh)
    project=copy.deepcopy(source);project.update(id=fresh['id'],status='draft',video_id='',video='',versions=[],
        editorial_brief=dict(source['editorial_brief'],privacy_status='private'),audio_settings={})
    project.pop('privacy_status',None);folder=studio._dir(project['id'])
    for key,name in [('voice','narration.wav'),('word_boundaries','word_boundaries.srt'),('subtitles','subtitles.srt')]:
        src=Path(source['voice']).with_name('narration.wav') if key=='voice' else Path(source[key])
        shutil.copy2(src,folder/name);project[key]=str(folder/name)
    studio._save(project);studio.configure_audio(project['id'],{'equalize':True,'compress':True})
    music=studio.select_music(project['id'],'ambient','Science & Space')
    url=source['sources'][0]['url'];timings=[]
    plans=[(0,'fact_card','reveal','Una nueva etapa',['Una región inexplorada']),
           (2,'timeline','timeline','Etapas del viaje',['Lanzamiento: 2021','Más de 3.500 millones de km']),
           (3,'comparison','before_after','Llegar no es sobrevolar',['Entrada en la región','Encuentro previsto: 2027']),
           (4,'scientific_schematic','path','Los troyanos orbitan el Sol',['Asteroides troyanos','Sol']),
           (6,'process_diagram','move','Estabilidad orbital',['Sol y Júpiter','Regiones troyanas'])]
    for index,kind,animation,title,labels in plans:
        scene=project['storyboard'][index]
        phrases={0:['Una nave'],2:['El viaje comenzó','Desde entonces'],
                 3:['Pero llegar','El primer encuentro'],4:['Estos asteroides','alrededor del Sol'],
                 6:['La gravedad','regiones estables']}[index]
        spec={'kind':kind,'title':title,'animation':animation,'items':[{'label':v,'source_url':url} for v in labels],
              'cue_phrases':phrases,'cue_occurrences':[1]*len(phrases)}
        if kind=='scientific_schematic':spec['relations']=[{'source':0,'target':1,'label':'orbitan'}]
        result=studio.generate_graphic(project['id'],scene['id'],spec)
        assert studio.generate_graphic(project['id'],scene['id'],spec)['reused']
        timings.append({'scene_id':scene['id'],'phrases':phrases,'resolved':result['spec'],
                        'animation':result.get('animation')})
    video=studio.render_video(project['id']);qa=studio.review_video(project['id'])
    assert not qa['issues'],qa['issues']
    assert studio._hash(Path(source['video']))==before
    report={'project_id':project['id'],'video':video,'qa':qa,'music':music,'animations':timings,
            'published_source_unchanged':True,'uploaded':False}
    write_json(folder/'animation_timing.json',timings)
    write_json(folder/'qa.json',qa)
    write_json(folder/'audio_analysis.json',{'master':json.loads((folder/'audio_master.json').read_text(encoding='utf-8')),
                                          'final_mp4':qa['full_stream_quality']})
    write_json(folder/'acceptance.json',report)
    write_json(Path('output/av_upgrade/complete_acceptance.json'),report)
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()

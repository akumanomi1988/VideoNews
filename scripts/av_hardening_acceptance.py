"""Local acceptance using a separate Lucy clone; never publishes or changes originals."""
import copy
import hashlib
import json
import shutil
from pathlib import Path
from scripts.studio_mcp import VideoNewsStudio


def main():
    studio=VideoNewsStudio()
    source=studio.get_project('a32e5c2505fc454d96c3f734f3b3a469')
    original=Path(source['video']);before=studio._hash(original)
    marker=Path('output/av_upgrade/hardening_acceptance.json')
    fresh=(studio.get_project(json.loads(marker.read_text(encoding='utf-8'))['project_id'])
           if marker.is_file() else studio.create_project('Local WAV and acoustically timed graphics acceptance','long'))
    studio._require_editable(fresh)
    project=copy.deepcopy(source)
    project.update(id=fresh['id'],status='draft',video_id='',video='',versions=[],
                   editorial_brief=dict(source['editorial_brief'],privacy_status='private'))
    project.pop('privacy_status',None)
    project.pop('owner_authorization',None)
    folder=studio._dir(project['id'])
    for key,name in [('voice','narration.wav'),('word_boundaries','word_boundaries.srt'),('subtitles','subtitles.srt')]:
        source_path=Path(source['voice']).with_name('narration.wav') if key=='voice' else Path(source[key])
        target=folder/name;shutil.copy2(source_path,target);project[key]=str(target)
    studio._save(project)
    studio.select_music(project['id'],mood='none')
    url=source['sources'][0]['url']
    scenes=project['storyboard']
    for index in (0,2,4):
        scene=scenes[index]
        spec={'kind':'timeline' if index==2 else 'fact_card','title':
              {0:'Lucy: una nueva etapa',2:'Un viaje de cinco años',4:'Una órbita alrededor del Sol'}[index],
              'items':[{'label':{0:'Lucy entra en la región troyana',2:'Lanzamiento en octubre de 2021',
                                4:'Los troyanos orbitan alrededor del Sol'}[index],'source_url':url}],
              'animation':'reveal' if index!=4 else 'none'}
        if index!=4:spec['cue_word_indices']=[0]
        studio.generate_graphic(project['id'],scene['id'],spec)
        # Repeat the same request: it must not append a duplicate scene asset.
        result=studio.generate_graphic(project['id'],scene['id'],spec)
        assert result['reused']
    result=studio.render_video(project['id'])
    qa=studio.review_video(project['id'])
    assert before==studio._hash(original),'Published source changed'
    evidence={'project_id':project['id'],'render':result,'qa':qa,'published_source_unchanged':True,
              'timing':'Actual word-boundary indices; no free timestamps','youtube_upload':False}
    (folder/'acceptance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    Path('output/av_upgrade/hardening_acceptance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=True))


if __name__=='__main__':main()

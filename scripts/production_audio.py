"""Strict project audio contract and cached, measured PCM mastering."""
import hashlib
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from scripts.atomic_storage import write_json
from scripts.audio_engine import export_audio


class AudioSettings(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    highpass: bool=False
    equalize: bool=False
    compress: bool=False
    music_level: float=Field(default=.12,ge=0,le=.3)
    ducking: float=Field(default=6.,ge=2,le=12)
    bitrate_kbps: int=Field(default=320,ge=96,le=320)


def master(source, music, settings, folder):
    settings=AudioSettings.model_validate(settings)
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    key={'voice':digest(source),'music':digest(music) if music else None,'settings':settings.model_dump()}
    folder=Path(folder);output=folder/'mastered.wav';receipt=folder/'audio_master.json'
    if output.is_file() and receipt.is_file():
        try:
            saved=json.loads(receipt.read_text(encoding='utf-8'))
            if saved.get('key')==key and saved.get('sha256')==digest(output):return output
        except (OSError,ValueError):pass
    report=export_audio(source,output,music=music,level=settings.music_level,ducking=settings.ducking,
                        highpass=settings.highpass,equalize=settings.equalize,compress=settings.compress)
    write_json(receipt,{'key':key,'sha256':digest(output),'measurement':report,'normalization_passes':1})
    return output

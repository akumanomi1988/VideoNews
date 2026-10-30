# Conversational Editorial Workflow

VideoNews separates conversational editorial reasoning from deterministic studio execution. ChatGPT owns intent interpretation, comparison, recommendation, narrative writing and storyboard decisions. The Python service validates the resulting brief, versions it, manages assets, renders media and enforces publication policy.

## Conversation intents

| Intent | Expected MCP actions | Must stop before |
| --- | --- | --- |
| Explore options | `research_news`, optionally `retrieve_article` | project creation or production |
| Recommend a candidate | news/source retrieval and a reasoned response | saving a production brief or producing media |
| Delegate selection | research and source retrieval; create a `proposed` brief with alternatives | production until the user approves |
| Create | reuse the exact active, approved project; script, storyboard and production tools | YouTube upload unless explicitly requested |
| Create and publish | research, choose, persist approved brief, produce, `review_video`, then `publish_youtube` | any failed QA or owner policy restriction |
| Revise | update the active project's brief and only affected artifacts | publication unless explicitly requested |

An exploration shortlist is conversation state, not an implicit project. The current shortlist controls ordinal references such as “the second one”. Project IDs scope persisted briefs and prevent a revision from leaking into another project.

## Brief schema and state

`chatgpt-plugin/schemas/editorial-brief.schema.json` is the MCP-facing JSON Schema for `save_editorial_brief`; `scripts/studio_mcp.py` also performs URL, bounds, field and cross-field validation. The project stores the brief and bounded version history. The selected primary URL must be among the verified source records. `format` and `aspect_ratio` are coupled. A proposal is not producible until `approval_status` is `approved`.

The owner-controlled publication policy is a separate boundary. A brief cannot enroll, broaden, or revoke that policy. The approved brief's privacy mode must match the requested upload mode and the Windows policy.

## Dependency invalidation

| Brief change | Cleared or invalidated | Preserved |
| --- | --- | --- |
| Selected story, verified sources, angle, tone, audience, language, concept or hook | narration, storyboard, visuals, voice, word boundaries, subtitles, video and approvals | unrelated projects |
| Target duration | script/narration, voice, word boundaries, subtitles and video | story-matched visuals and image provenance |
| Visual strategy or image sources | visuals, linked assets, video, preview, thumbnail and approvals | sourced story and narration |
| Format/aspect ratio | video, preview, thumbnail and approvals | voice, subtitles and story content |
| Destination or privacy | publication review/approval state | editorial and media artifacts |

Any content change moves a previously approved brief back to `proposed`; the user can approve the revised brief without re-answering unchanged preferences. Approval status alone can be changed without clearing media.

## Production and quality gates

The renderer must use the approved format and aspect ratio. After Edge TTS, Studio probes actual audio duration and enforces `max(duration_tolerance_seconds, 10% of target)`; final render repeats the duration check and requires 1080×1920 for Shorts or 1920×1080 for landscape. `review_video` checks the final media streams, codecs, source link, approved brief, metadata, subtitle parse/timing and storyboard-to-asset coverage. The report still requests editorial fact review; structural checks do not establish truth, image meaning or human-readable typography.

Rendering and upload remain separate actions. A review issue blocks publishing. Public uploads require local owner enrollment or a matching one-use owner authorization, and the YouTube Data API readback must confirm channel and effective privacy. An uncertain upload is reconciled, never replayed.

NewSphere Cinematic uses Azure MAI as its primary visual provider when paid image generation is enabled and Azure credentials are configured. The checked-in example enables this setting; local endpoint and API credentials must still be supplied. Azure calls can incur charges. Pexels is secondary and runs only after an explicit stock selection in the approved brief; generation failures never switch silently to stock. Original graphics and the validated manual image-import flow remain available.

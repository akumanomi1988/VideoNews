# NewSphere editorial and production standard

Default to Spanish from Spain, landscape 1920x1080 and a 240-second target within
180-300 seconds. The minimum for this long-form workflow is 180 seconds. Explicit
user instructions may establish a different brief; do not rewrite historical
projects or silently switch orientation. Check the actual encoded file, not just
requested provider settings. A short or vertical result cannot fulfill a long-form brief.

## Editorial and narrative direction

Research original and corroborating sources. Preserve dates, names, statistics,
attribution and the difference between confirmation, hypothesis, interpretation
and prediction. Check published-topic history and identify a new angle before
repeating a story. Define the concrete question the video answers.

Open in 0-10 seconds with a supported fact, question, conflict or consequence.
Use 10-30 seconds for essential context and the informational promise. Develop
the explanation through facts, examples and consequences. Finish with a useful
conclusion, implications and a relevant question. No generic welcome, filler,
repeated explanations, unsupported sensationalism or inflated claims of exclusivity.
Write for oral narration with concise paragraphs and natural transitions. Extend
research or choose another angle if the topic cannot sustain three useful minutes.
Never pad with silence, duplicate images or deliberately slow speech.

## Audiovisual direction

Use the visual-direction reference and plan a meaningful variation approximately
every 5-10 seconds, adjusted to content. Each scene must advance the narrative.
Compose images natively for landscape; reject or regenerate vertical provider
results. Editorial cropping can preserve geometry, but stretching is forbidden.
Use original AI illustrations, authorized documentary assets, original explanatory
graphics and maps with traceable provenance. Do not repeatedly zoom one image
to simulate variety. Stay within configured paid-generation limits; use useful
original graphics or agree on a different budget instead of silently increasing it.

Keep image files clean: do not bake a large synthetic-media banner into them.
The renderer overlays a small circular `IA` badge in the lower-left safe zone
only during scenes marked synthetic. Preserve provenance, description credits
and the appropriate YouTube synthetic-content declaration. The small badge does
not turn an invented reconstruction into evidence: never imply it is documentary.

Use the configured Spanish voice and check pronunciation of names, numbers and
technical terms. Verify actual TTS duration and word-based subtitle synchronization.
Use legible landscape captions and safe placement. Background music must have
documented compatible rights, remain subordinate to speech and avoid clipping.
If no licensed track is configured, report that fact; do not invent a license or
claim a listening review based only on loudness measurements.

## Packaging

Prepare three distinct, accurate title candidates and two different thumbnail
concepts. Save them as `title_candidates` (three strings) and `thumbnail_concepts`
(two strings) using `save_youtube_metadata`, along with the chosen title and
thumbnail concept. Titles and thumbnails should complement each other.
The actual thumbnail must be landscape and readable on mobile, normally with
3-5 emphasized words. Provider-rendered text is acceptable only after spelling
and readability inspection; deterministic text composition is the fallback.
Preserve an informative description, relevant tags, sources and resource credits.

## Five gates before publication

Report each gate with evidence and any limitation; a successful API call or file
probe alone cannot establish editorial quality.

- **A / Editorial accuracy:** inspect important claims against sources, dates and
  statistics; preserve references and exclude unsupported claims.
- **B / Narrative:** review the opening, coherent development, rhythm and absence
  of filler. This is editorial judgment, not an invented retention score.
- **C / Video:** inspect actual format, resolution, minimum/approved duration,
  geometry, scene coverage, representative frames, transitions and alignment.
- **D / Audio:** verify complete narration, pronunciation when listening is
  available, intelligibility, mix and subtitle synchronization. Distinguish actual
  listening from automated measurements.
- **E / Publication:** inspect selected title, description, thumbnail, tags,
  language, credits, provenance/rights and editorial review status. Then check
  owner authorization, target channel, requested privacy and idempotency.

Repair critical failures and rerun the affected checks. Do not publish publicly
with factual review pending. Keep the result local until reviewed, or private if
the owner policy authorizes a private upload. A public-only policy is not permission
to bypass pending factual review. Editorial approval never creates owner consent.

After a production, return the topic/angle, final title, measured duration,
resolution/aspect, actual voice/image providers, A-E gate results, principal
sources, confirmed YouTube URL/privacy if uploaded, and problems/corrections.
Optimize informational value and sustained interest; do not equate technical
success with a finished editorial product or promise audience performance.

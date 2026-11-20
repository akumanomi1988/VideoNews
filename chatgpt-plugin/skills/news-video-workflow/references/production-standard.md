# NewSphere editorial and production standard

Default to Spanish from Spain, landscape 1920x1080 and a 240-second target within
180-300 seconds. The minimum for this long-form workflow is 180 seconds. Explicit
user instructions may establish a different brief; do not rewrite historical
projects or silently switch orientation. Check the actual encoded file, not just
requested provider settings. A short or vertical result cannot fulfill a long-form brief.

## Editorial and narrative direction

By default, focus on Spain: events in Spain, Spanish institutions and people,
and developments with a direct, material effect on people in Spain. Search
across Spanish regions and subject areas. Choose an international story only
when its importance is exceptional and its relevance to the Spanish-speaking
audience can be explained concretely. Follow an explicit user-requested topic
or geography when provided. When no topic is set, break ties between comparable,
well-sourced Spanish candidates in this order: politics, weather and climate,
then high-impact/sensational stories with concrete human consequences. This is
only a tie-breaker: freshness, corroboration and accuracy come first, and
sensational framing must never be invented or exaggerated.

Research original and corroborating sources. Preserve dates, names, statistics,
attribution and the difference between confirmation, hypothesis, interpretation
and prediction. Check published-topic history and identify a new angle before
repeating a story. Define the concrete question the video answers.

Open in 0-12 seconds with the NewSphere branded welcome that names this story in
one concrete phrase ("Bienvenidos a NewSphere. Hoy vamos a hablar de…"), without
revealing the payoff. Use 12-25 seconds for the sharpest supported tension, then
one short like/subscribe/bell CTA with the comment question "¿qué cambiarías tú?"
by ~35 seconds. Use the next stretch for the informational promise and a specific
"hoy vamos a ver" roadmap plus the first hard fact before ~55 seconds. A second
CTA is optional, only after minute two and only at a natural break. Develop the
explanation through facts, examples and consequences, then finish with a useful
conclusion and practical implications that resolve the opening promise, followed
by a brief branded despedida with one final CTA and a forward hook. Add a question
only when it contributes something new. No channel biography, filler, repeated
explanations, unsupported sensationalism, invented urgency or inflated claims of
exclusivity.

Sound passionate and convinced: human stakes first, concrete verbs, direct
address, controlled contrast and a rising build to the payoff. Passion is not
volume: no ALL CAPS, stacked exclamations, fake outrage or doom adjectives the
sources do not support. In stories involving death, injury or distress, keep
gravity and respect; no triumphalism and no jokes.
Write for oral narration with concise paragraphs and natural transitions. Extend
research or choose another angle if the topic cannot sustain three useful minutes.
Never pad with silence, duplicate images or deliberately slow speech.

## Audiovisual direction

Use the visual-direction reference and plan a meaningful variation approximately
every 5-10 seconds, adjusted to content. Each scene must advance the narrative.
Render every illustration in the approved `RUBBER_HOSE` style: 1930s hand-inked
cartoon, thick contours, cream/mustard/terracotta/faded-teal palette, anonymous
characters, no lettering. Keep sensitive stories respectful and never comic.
Compose images natively for landscape; reject or regenerate vertical provider
results. Editorial cropping can preserve geometry, but stretching is forbidden.
Use original AI illustrations, authorized documentary assets, original explanatory
graphics and maps with traceable provenance. Do not repeatedly zoom one image
to simulate variety. Stay within configured paid-generation limits; use useful
original graphics or agree on a different budget instead of silently increasing it.
Treat 5-10 seconds as an editorial planning guide, not evidence that the renderer
made a cut. Plan supported visual changes inside the actual scene/asset budget:
source-bound graphics, narration-anchored reveals, varied compositions or licensed
material explicitly selected for this project. Inspect the resulting timeline.
A new zoom on the same image is not a new explanatory visual. If coverage is weak,
repair the relevant storyboard beat before rendering rather than claiming the
desired rhythm was achieved from requested settings alone.

Keep illustrations, thumbnails and video exports free of IA badges. Preserve
asset provenance and use the YouTube declaration described in the packaging
guidance. Present editorial illustrations as illustrations and use verified
documentary material for evidence.

Use the configured Spanish voice and check pronunciation of names, numbers and
technical terms. Verify actual TTS duration and word-based subtitle synchronization.
Use legible landscape captions and safe placement. Background music must have
documented compatible rights, remain subordinate to speech and avoid clipping.
If no licensed track is configured, report that fact; do not invent a license or
claim a listening review based only on loudness measurements.

## Packaging and discovery

Treat packaging as part of editorial quality, not a label applied at the end.
Apply [packaging and SEO guidance](packaging-seo.md) before every metadata save:
searchable subject, honest promise, matching thumbnail and opening, and tags a
Spanish viewer would actually use. Optimize for clarity and discovery; never use
invented urgency, inflated exclusives, keyword stuffing or fabricated metrics.

Defaults that must hold:

- Title at most 90 characters (the uploader truncates there), ideally 55-75, with
  the named subject in the first stretch. No ALL CAPS, emojis or filler.
- Description opening 1-2 lines readable on their own and carrying the main entity
  and topic phrase; then why-now, 3-5 scope bullets, dated sources and credits, plus 2-3 clickable hashtags in the text. Author around or
  below 3800 characters because the uploader appends the channel text.
- 10-15 natural Spanish tags across broad, entity, topic, region and brand terms,
  kept under 500 total characters; the current uploader publishes tags, not the
  separate `hashtags` field.
- Thumbnail: one large Rubber Hose gesture, expression or prop that conveys
  the stakes at phone size, plus 3-6 words naming the topic or consequence.
  Select its source with `thumbnail_scene_id`, use
  `thumbnail_layout="rubber_hose"` and inspect the actual 1280x720 export.

Prepare three distinct, accurate title candidates (direct headline, consequence
and contrast) and two different thumbnail concepts. Save them as
`title_candidates` (three strings) and `thumbnail_concepts` (two strings) using
`save_youtube_metadata`, along with the chosen title, thumbnail concept and text.
Titles and thumbnails must make the same promise as the opening narration.
Provider-rendered text is acceptable only after spelling and readability
inspection; deterministic text composition is the fallback. Preserve an
informative description, relevant tags, sources and resource credits.

## Five gates before publication

Report each gate with evidence and any limitation; a successful API call or file
probe alone cannot establish editorial quality.

- **A / Editorial accuracy:** inspect important claims against sources, dates and
  statistics; preserve references and exclude unsupported claims.
- **B / Narrative:** apply the script-direction entertainment edit before TTS.
  Verify the retention structure: a short branded welcome naming this story, the
  true tension by ~20 s, one like/subscribe/bell CTA plus the "¿qué cambiarías
  tú?" comment question by ~35 s, a specific "hoy vamos a ver" roadmap and first
  hard fact before ~55 s, a resolved payoff and a short branded despedida with a
  final CTA. Review an actual opening and middle passage for conversational
  energy, passion, personality, an understandable concrete example and useful
  changes of beat. Check humour fits the subject, secondary figures do not become
  a spoken catalogue, explanations are not repeated, and the ending lands a
  payoff. Rewrite flat passages even when their facts are correct. Review the
  final sequence again after rendering. This is editorial judgment, not an
  invented retention score or a claim of listening when none occurred.
- **C / Video:** inspect actual format, resolution, minimum/approved duration,
  geometry, scene coverage, representative frames, transitions and alignment.
- **D / Audio:** verify complete narration, pronunciation when listening is
  available, intelligibility, mix and subtitle synchronization. Distinguish actual
  listening from automated measurements.
- **E / Publication and packaging:** inspect the selected title, description,
  thumbnail, tags, hashtags, language, credits, provenance/rights and editorial
  review status. Confirm the title/thumbnail/opening promise matches, the opening
  description lines carry the searchable subject, tags are useful rather than
  stuffed, and nothing overclaims. Then check owner authorization, target
  channel, requested privacy and idempotency.

Repair critical failures and rerun the affected checks. Do not publish publicly
with factual review pending. Keep the result local until reviewed, or private if
the owner policy authorizes a private upload. A public-only policy is not permission
to bypass pending factual review. Editorial approval never creates owner consent.

After a production, return the topic/angle, final title, measured duration,
resolution/aspect, actual voice/image providers, A-E gate results, principal
sources, confirmed YouTube URL/privacy if uploaded, and problems/corrections.
Optimize informational value and sustained interest; do not equate technical
success with a finished editorial product or promise audience performance.

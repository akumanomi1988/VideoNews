# YouTube packaging, SEO and discovery (NewSphere)

Packaging exists to get the right Spanish viewer to a truthful video: the title,
thumbnail, first description lines and tags must describe what the video actually
delivers. Optimize for clarity, searchable entities and an honest promise, never
for invented urgency, inflated claims or trap-click curiosity.

Read this before every `save_youtube_metadata` call.

## Hard limits of the current Studio uploader

- **Title:** stored 5-100 characters; `publish_youtube` truncates to 90. Write at
  most 90, and keep the load-bearing words inside the first ~55-60 so the mobile
  and search-result cut never hides the subject.
- **Description:** the uploader appends the channel description and a `#tag`
  line, then truncates the whole result at 5000 characters. Author at most about
  3800 characters so your sources and credits are never clipped.
- **Tags:** up to 30 are accepted, but the uploader lowercases them, strips
  punctuation, drops tags under 3 characters, de-duplicates, and keeps at most
  15 tags within 500 total characters. Author the final 10-15 directly; do not
  rely on truncation.
- **Hashtags:** the `hashtags` field is stored but the current uploader does not
  publish it. Put the 2-3 hashtags you want clickable (e.g. `#Constitución
  #España`) inside the description text itself, at the start or just before the
  sources.
- Accented characters, `ñ`, `¿` and `¡` survive normalization, so keep correct
  Spanish orthography. Punctuation such as `#` or `:` is stripped from tags.
- Category 25 (News & Politics) and language `es` are the defaults.

## Title

Write a direct news headline. Lead with the searchable actor or topic and say
what happened, what was proposed or what changes. Name the most concrete
consequence the video explores. Use verbs such as “propone” when the measure
still depends on approval. Prefer a statement to a vague curiosity question.

Good shapes:

- `Frente Amplio propone alquiler público asequible y reducir la jornada laboral`
- `Por qué tu factura de la luz sube aunque baje el precio: la clave`
- `AEMET avisa: la borrasca llega el jueves y estas son las zonas en riesgo`
- `Alquiler en Madrid: el dato que explica por qué no baja`

Rules:

- Name the actor, place or institution people already search (Sánchez, PSOE, BOE,
  AEMET, Renfe, Madrid, Andalucía...). Put it near the front.
- Prefer the concrete term a viewer would type: `reforma constitucional`,
  `precios de la vivienda`, `alerta meteorológica`, not clever wordplay alone.
- Use a true, meaningful number when it helps; a date only when the date is the
  news. Never invent statistics or percentages to look precise.
- Do not write in ALL CAPS, add emojis, or litter the title with a date bracket
  such as `[2026]` unless the year is essential and factual.
- Avoid `¡No te lo vas a creer!`, `increíble`, `exclusiva`, `urgente`, `AHORA`
  and similar phrases unless the story is genuinely breaking and sourced.
- One colon at most; no stacked clauses; no keyword lists.

Save three candidates of different kinds and state which is selected:
direct headline, consequence and contrast. The selected title, the
thumbnail words and the opening narration must make the same promise.

## Description

The first 1-2 lines are what a viewer sees before "más información". They must
stand alone, carry the main entity and topic phrase, and preview the answer.

Suggested structure (blank line between blocks):

1. **Opening 1-2 lines:** plain summary with the main entity, the concrete stake
   and the promise. Roughly 100-150 characters, keyword-bearing, no greeting or
   subscription request.
2. **Why now / what it changes:** a short paragraph with the current event, the
   date of the event, and the consequence closest to the viewer.
3. **What the video covers:** 3-5 short bullets, each a searchable phrase, so the
   scope is obvious and the page reads well on mobile.
4. **Sources:** publisher, event/publication date and canonical URL for each
   source, as required by the editorial standard.
5. **Credits:** original script, voice and visual production credits, and
   music status. Omit a blanket AI notice for clearly non-realistic art.
6. **Hashtags:** 2-3 relevant ones written into the text (`#España`,
   `#Constitución`, `#NewSphere`).

Write naturally around the real search terms; never stuff keywords or repeat a
phrase to hit a length. Do not put the tags block, credits or hashtags before the
opening summary.

Use `contains_synthetic_media: false` for clearly non-realistic illustrations and generic narration that does not impersonate a real person, when there is no other content requiring disclosure. Use `true` when [YouTube requires disclosure](https://support.google.com/youtube/answer/14328491), for example realistic synthetic scenes, altered footage of real events, cloned voices of other people or AI-generated music.

## Tags

Build 10-15 tags that mix, without duplicates:

- 1-2 broad Spanish terms (`españa`, `actualidad`, `política`, `economía`,
  `meteorología`).
- 2-4 named entities from the story (people, institutions, places, laws, brands).
- 2-4 specific topic phrases a viewer would search (`reforma constitucional`,
  `precio de la vivienda`, `alerta por lluvias`, `pensiones`).
- 1-2 region or beat terms (`andalucía`, `madrid`, `congreso`).
- The brand tag `NewSphere`.

Keep each tag 3-60 characters, natural Spanish, no hashtags, no misspellings, no
unrelated trending terms and no other channels' names. Total must stay under 500
characters. Prefer the words already used in the title and opening lines over
synonym padding.

## Thumbnail illustration and text

- Make the visual hook bold. Stage one instantly recognizable action with a
  close crop, a big silhouette, exaggerated Rubber Hose gestures or expressions,
  and strong contrast. Make the relevant prop large enough to read at phone
  size. Exaggerate the drawing, while keeping the events and claims factual.
- Plan two thumbnail concepts before generating visuals. For the selected
  concept, use a relevant storyboard scene and frame it so the key gesture and
  prop stay above the lettering. Set `thumbnail_scene_id` to that scene instead
  of relying on the default first image. Avoid generic desks and small collages.
- Write 3-6 plain words in `thumbnail_text`. Name the topic or the concrete
  stake. Repeating the subject is fine when it makes the thumbnail stand alone.
  Avoid generic lines such as “¿Qué notarás tú?” that could fit any story.
- Example for a policy explainer: a cartoon figure turns oversized empty pockets
  inside out in a close-up, with `Propuestas de Frente Amplio` on the card.
  The gesture represents household finances. The title names the actual
  proposals covered and does not suggest the party caused the hardship.
- Use `thumbnail_layout="rubber_hose"` for the branded look: 1930s cream ink card,
  thick black lettering with a warm offset shadow, source scene in the same
  Rubber Hose style. `overlay` remains valid for a classic lower-third card and
  `framed` for scenes that must not be cropped.
- Put the numbers or short phrase that carries the story in `thumbnail_text`, not
  a full sentence. In Spanish, plain numerals read better at small size.
- For tragic stories, choose a respectful tension (weather, distance, empty
  objects), no grinning caricatures and no disaster spectacle.
- Never fabricate a document, headline, figure or official seal; never imply an AI
  illustration is photographic evidence.
- Check the 1280×720 export at phone size. The focal gesture and text must both be
  readable without zooming. Adjust the art selection or shorten the copy if
  either gets lost.

## Integrity rules (non-negotiable)

- Every packaging claim must be supported by the saved sources; label hypotheses
  and examples as such.
- Never invent audience size, search volume, virality, view counts or expected
  performance. SEO choices are editorial judgment, not measured data.
- Do not manufacture urgency, countdowns or "última hora" for a non-breaking
  story.
- Keep the agent's deliberate footer/tag suffix in mind: the uploader may append
  the channel text and `#tag` line, so do not duplicate it yourself.

## Pre-save checklist

- Title at most 90 characters (ideally 55-75), names the searchable subject, and
  matches the thumbnail and the opening promise.
- Opening description lines are understandable alone and contain the main entity
  and topic phrase.
- 3-5 scope bullets, sources with dates and URLs, credits
  and 2-3 clickable hashtags all present; authored description around or below
  3800 characters.
- 10-15 tags covering broad, entity, topic, region and brand; under 500 total.
- Three title candidates and two thumbnail concepts saved; selection stated.
- Read back the saved metadata before generating the thumbnail and running QA.

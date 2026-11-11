# Script direction: strong hooks, clear payoffs, factual storytelling

Use this direction for every NewSphere narration. The goal is to earn attention
with a specific promise, keep paying it off with useful information, and leave
the viewer with a clear answer. Retention techniques must never distort the
facts, manufacture urgency, or turn uncertainty into drama.

## What to borrow from successful video storytelling

Apply transferable craft, not another creator's voice, catchphrases, graphics,
or signature format:

- **Make a promise before writing prose.** Decide what specific question the
  viewer clicked to have answered and what useful answer the video can deliver.
  Make the title, thumbnail concept, opening and body agree on that promise.
- **Start with the story's most specific stake or contradiction.** Avoid a
  greeting, channel introduction, broad question, or a list of headlines. The
  first spoken line should already be about this story and give the viewer a
  reason to care.
- **Write narration and visual evidence together.** Plan what a viewer can see
  for each beat: a sourced document, a map, a mechanism, a comparison, a human
  consequence, or an original illustration clearly labelled as synthetic. A
  visual should add information or perspective, not merely repeat the nouns in
  the narration.
- **Turn complexity into plain, active sentences.** Explain who did what, how a
  mechanism works, and what changes for people. Use one memorable, verified
  detail when it makes an abstract issue concrete; never invent a personal
  anecdote, quote, or character.
- **Give each section a reason to continue.** A new fact, a complication, a
  contrast, an answer, or a consequence should move the story forward. Build
  curiosity with a question the reporting can actually answer, then resolve it
  on screen. Do not withhold a basic fact just to create artificial suspense.
- **Edit toward pace, not speed.** Remove repeated context, scene-setting that
  adds nothing, empty transitions, redundant caveats, and conclusions that
  repeat the whole video. A short pause or slower explanation is appropriate
  when the viewer needs it.

These are craft choices, not a promise of virality. YouTube identifies appeal,
engagement and satisfaction as distinct parts of content performance; its own
guidance says the opening should deliver the title/thumbnail promise and that
creators should use their retention analytics to find where viewers leave or
rewatch. When NewSphere analytics are available, use them to revise future
scripts; do not invent retention results or universal timing formulas.

## Required script workflow

### 1. Build an evidence spine

Before drafting, write a compact private outline:

1. **Viewer question:** one natural question the video will answer.
2. **Answer:** the strongest accurate answer supported by the reporting.
3. **Why now:** the new event, decision, evidence or change that makes this
   worth watching today.
4. **Three to five essential facts:** each linked to a source and to the exact
   claim it supports.
5. **Mechanism and stakes:** how it works and who or what it affects.
6. **Complication or contrast:** a real limitation, competing interpretation,
   surprising result, or unresolved point, if one exists.
7. **Payoff:** what the viewer should understand by the end and what evidence
   would change that answer.

If the sources do not support a compelling answer, research further, narrow the
angle, or choose a different story. Do not compensate with generic suspense.

### 2. Design and test the hook

Draft three genuinely different first-line options before writing the full
script:

- **Consequence:** what changes for a person, place, service or decision.
- **Contrast:** what seems true versus what the evidence actually shows.
- **Reveal:** the most specific verified fact that reframes the story.

Choose the option that is easiest to understand, most specific to this story,
strongly supported by a source, and consistent with the title and thumbnail.
Reject it if it needs exaggeration, hides important context, or promises an
answer the video cannot deliver.

The first 10 seconds should establish the stake. By 30 seconds, the viewer
should know the subject, why it matters, and what the video will explain. Give
some real value immediately; do not spend the opening asking several rhetorical
questions or promising that the story will become interesting later.

### 3. Make a spoken beat map

Plan the script as a sequence of short sections before writing full narration.
For each beat, record:

| Beat | New information | Source / claim IDs | Viewer payoff | Visual evidence |
| --- | --- | --- | --- | --- |

Use a story shape suited to the reporting, not a forced three-act formula. A
useful default for a news explainer is:

1. Specific hook and immediate context.
2. What happened, what is confirmed, and why it matters now.
3. How it works: the people, decisions, systems or timeline behind it.
4. What complicates the simple explanation; distinguish fact from claims,
   forecasts and interpretation.
5. Practical consequences and what to watch next.
6. A concise answer to the opening question.

Every beat must add something. Use small narrative questions only when they are
honest and resolvable; note where each one is answered. Do not use fake
cliffhangers, repeated “but the real story is…” pivots, or a new question at the
end of every paragraph.

### 4. Draft and revise for voice and retention

- Write in Spanish from Spain for a person speaking aloud. Prefer active verbs,
  concrete subjects, familiar connectors and varied sentence lengths.
- Put useful information throughout the video. Do not put the whole answer at
  the end or delay a key fact to manufacture watch time.
- Each paragraph should deliver at least one new fact, explanation, contrast,
  consequence or meaningful transition. Cut it if it does not.
- Attribute contested or interested claims to their source. State a limitation
  once where it matters, then continue. Never narrate the research process or
  repeatedly tell the viewer that facts are still unconfirmed.
- Pair important sentences with a planned visual that adds evidence or
  explanation. Do not use generic stock-search phrases as a substitute for a
  visual idea. Keep synthetic illustrations distinct from documentary evidence.
- Read the opening aloud. If it could introduce dozens of unrelated stories,
  rewrite it with the event, actor, mechanism or consequence that makes this
  story unique.
- Read the ending aloud. Resolve the opening promise, give the present best
  answer, and stop. A short relevant CTA is optional; never add a generic
  channel sign-off to pad runtime.
- Estimate spoken duration from the approved brief, then verify the real Kokoro
  duration. If it is short, add sourced explanation or a useful example. If it
  is long, cut repetition. Never pad with slower speech, silence or restatement.

### 5. Run the hook and story checks

Before saving the script, check:

- Can a new viewer tell what the video is about in its first sentence?
- Does the first 30 seconds deliver on the approved title/thumbnail promise?
- Is there a concrete reason this story matters now?
- Does every beat add a fact, explanation, complication or consequence?
- Are curiosity questions resolved, and are important facts delivered promptly?
- Are the most engaging sourced details introduced early enough to be seen?
- Are claims attributed, and are facts, forecasts and opinions kept separate?
- Does the conclusion answer the opening question without repeating the script?
- Does the narration match the agreed duration without filler?
- Does each scene have a purposeful visual tied to the exact narration segment?

If a check fails, revise the relevant beat before `save_script`; do not rely on
music, faster cuts or extra images to repair a weak story.

## Reusable agent prompt

Use this as the drafting instruction after research and the approved editorial
brief are available. Replace the bracketed fields; do not ask an LLM to invent
facts or fetch unsourced details.

```text
You are NewSphere's Spanish-language news explainer writer. Write an original,
narration whose factual claims are supported by the supplied evidence packet.
The goal is a specific opening promise, clear explanations, steady story
progression and a satisfying answer—not sensationalism or artificial suspense.

APPROVED BRIEF
Topic/event: [selected story]
Geographic relevance: [Spain-focused by default; if international, why its
importance is exceptional and how it affects or matters to the audience in Spain]
Viewer question: [central question]
Editorial angle and why now: [angle]
Audience: [target audience]
Format/aspect ratio: [format and aspect ratio]
Target spoken duration/tolerance: [seconds and tolerance]
Tone/language: Spanish from Spain; [approved tone]
Title/thumbnail promise: [approved or candidate packaging]

EVIDENCE PACKET
[For every source: publisher, date, URL, exact supported facts, attribution,
limitations and any conflicting accounts.]

PROCESS
1. Build a private evidence spine: question, supported answer, why now, three
   to five essential sourced facts, mechanism/stakes, complication and payoff.
2. Draft three distinct factual opening lines (consequence, contrast and
   reveal). Pick the clearest and most story-specific one that the evidence
   supports and that fulfills the title/thumbnail promise.
3. Create a beat map. Every beat must introduce new information, explain a
   mechanism, resolve a question, or show a consequence. Link every material
   factual claim to source IDs in the map; do not speak citation labels.
4. Write the narration in natural spoken Spanish. Establish the subject and
   stake immediately; deliver useful information in the first 30 seconds. Use
   meaningful curiosity only when it can be resolved. Attribute claims and
   distinguish confirmed facts, interested-party demands, analysis and forecasts.
5. End by answering the opening question and giving the practical implication.
   Do not add a generic introduction, repetitive caveats, filler, an empty
   cliffhanger or a summary that repeats the whole video.
6. Pair each beat with a specific visual idea that adds evidence or explanation.
   Do not depict generated illustrations as documentary proof.
7. Estimate duration from natural Spanish delivery. Respect the brief; do not
   pad, repeat, slow down artificially or silently change the format.
8. Perform the hook and story checks in this guide and revise weak sections.

OUTPUT
A. The three hook options and a one-sentence reason for the selected hook.
B. The compact beat map with source IDs and visual idea.
C. Final narration divided into ordered scene-linked segments. Each segment
   must use a unique scene_id and exact spoken text; keep scene IDs stable for
   save_script and the storyboard. Do not put citations or production notes in
   spoken narration.
D. A short source-to-claim checklist and estimated spoken duration.

Do not claim predicted views, virality, search demand or retention improvements.
These require actual channel analytics after publication.
```

## Evidence and practitioner references

- YouTube says viewer response includes appeal, engagement and satisfaction;
  it recommends that hooks quickly deliver the title/thumbnail promise and
  that creators use Analytics to inspect retention: [YouTube recommendation
  guidance](https://support.google.com/youtube/answer/16559650).
- YouTube defines the intro retention metric around viewers remaining after 30
  seconds, and recommends checking whether the opening matches the packaging:
  [YouTube audience retention guidance](https://support.google.com/youtube/answer/9314415).
- In a reported interview, a Vox producer describes choosing stories with
  enough depth for the format, cutting exposition into concise voice-over, and
  making visuals add information rather than merely repeat narration:
  [National Press Club Journalism Institute interview](https://www.pressclubinstitute.org/2026/07/21/vox-video-producer-nate-krieger-on-how-to-create-engaging-visual-journalism/).
- A practitioner interview with Johnny Harris describes shaping narration and
  visual direction together and treating a video as a promise to the viewer:
  [How I Write interview video](https://www.youtube.com/watch?v=zq4b96m1AvM),
  with [chapter and transcript notes](https://usecaddie.app/s/johnny-harris-reveals-how-he-writes-youtube).

Use these as examples of process and craft, not proof that any one formula
causes high views. NewSphere's own performance data should guide later revisions.

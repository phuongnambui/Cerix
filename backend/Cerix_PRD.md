Cerix Product Requirements (PRD)
Living reference document. Phase 1. Personal project and portfolio piece.
Revision note (latest update)
This version folds in a few decisions I made while reviewing the design. The big one is that I split magnitude into two separate things, scale and confidence, where confidence is now a short state ladder (rumored, corroborated, confirmed) backed by a count of independent sources, instead of a second 1 to 10 number. Momentum rides on that confidence climbing. Category overlap is allowed now, except for Noise. The build order changed so that Evals comes before MCP, and MCP got cut down to one real job. Everything else is mostly the same as before.
1. What Cerix is
Cerix is an AI powered impact classifier for tech news. It is not a personalization engine and it is not a feed. It reads tech news and sorts it by what kind of importance it has and how confirmed it is, not by what I happen to be interested in and not by how much attention it got.
Core philosophy: every algorithm is optimised for engagement. Cerix is optimised for impact. They are not the same thing.
2. What Cerix is not
•	Not personalized. The classification never depends on who is reading. Two people see the same scores.
•	Not engagement driven. Likes, upvotes, reposts and view counts never feed into category, scale or confidence.
•	Not an objectivity claim I cannot back up. Calling this objective would be a stretch, since the model is still making judgment calls. The honest pitch is that it is consistent and defensible: the same criteria applied the same way every time. The evals are what let me claim that consistency credibly. Without them it is just an assertion.
3. Categories
Every story gets a category. The category answers what kind of important this is. There are five.
•	Industry Shifting: changes how the field works. New infrastructure, policy, or M and A that reshapes a market, or a foundational capability shift.
•	Cultural Moment: the mainstream, non technical world is about to know about this.
•	Hot: plugged in tech people should know this this week.
•	Insight: a high signal opinion or analysis, not a discrete event.
•	Noise: high engagement, low impact. Quarantined, not deleted.
Category overlap (decided this revision): a story can sit in more than one category at once if it genuinely is more than one kind of important, for example an acquisition that is both Industry Shifting and a Cultural Moment. The one exception is Noise. Noise is exclusive. If something is important enough to also be Industry Shifting then it is not Noise. Noise means Noise and nothing else.
4. Scoring: the two axes
This used to be one number called magnitude. I split it, because cramming scale and confidence into a single 1 to 10 number was ambiguous. A small but confirmed story and a huge but unconfirmed story could land on the same number, and you could not tell which was which from the number alone.
Scale (1 to 10): how big the story is if it is true. Judged from the content alone. This is the part the model is actually good at, reasoning about how much something would matter assuming it is real.
Confidence: how confirmed the story is. It is a short state ladder, not a number: rumored when a single source has it, corroborated when several independent sources have it, and confirmed when a primary or authoritative source has closed it. Underneath the state I keep the raw count of independent sources as supporting detail.
Confirmed is a state, not a count: the jump to confirmed happens when a primary source closes the story, not when the source count crosses some threshold. An official first party announcement maxes confidence even if it is literally the only source, because one company announcing its own raise outweighs five outlets speculating about it. This is exactly the case a pure count gets wrong, see the Day 10 example in section 8.
What counts as a primary or authoritative source: a first party announcement, an official filing or government action, the company or lab or body the story is about, or a peer reviewed publication. Everything else is secondary. Many secondary outlets reprinting one story reach the corroborated state at most, never confirmed on their own.
Why a state plus a count, and not another 1 to 10: two 1 to 10 numbers side by side read like a cockpit and force the reader to compare them. A scale number next to a one word confidence state reads as two different kinds of thing, so it does not feel like math. It is also more honest, since the model cannot truly verify a brand new claim the moment it appears. Confidence builds as real corroboration arrives, and only closes when a primary source closes it.
One more note: scale is not comparable across categories. A scale 7 Industry Shifting story and a scale 7 Cultural Moment story are measuring different things.
Confidence mechanics: independence and source tiers
Confidence rests on two judgments about each source: is it independent, and how credible is it. Both decide which state a story can reach. Neither ever touches scale or category.
Independence, judged per item. When a new article links to a thread, the model answers one narrow question: does it have its own original sourcing for the core claim, or does it just attribute the claim to a source already in the thread. Independent reporting counts toward the state. An echo (it only repeats a source already in the thread) still gets linked so I can show carried by N outlets, but it does not raise confidence. When the model is unsure it treats the item as an echo, because ambiguity should never inflate confidence. Every verdict comes with a one line reason, so it is auditable and can go into the evals.
Credibility is a small fixed set of tiers, not a score, so I do not sneak a vague number back in:
•	Tier A, primary or authoritative: the company, lab, or body the story is about speaking for itself, an official filing or government action, or a peer reviewed publication.
•	Tier B, established outlet: a credible newsroom or reputable trade outlet with editorial standards and a track record.
•	Tier C, unvetted: random blogs, anonymous posts, aggregators, content farms, unknown newsletters, social posts.
Most sources I ingest are known, so their tier lives in a maintained config table, which is deterministic and easy to audit. For an unknown source the model assigns a provisional tier with a reason, defaulting to Tier C when unsure.
How the two gate the states: a source only counts toward the confidence state if it is both independent and Tier B or higher.
•	confirmed: at least one Tier A source has closed the story. This overrides the count.
•	corroborated: two or more independent Tier B or higher sources.
•	rumored: one independent Tier B or higher source, or the story is currently carried only by Tier C sources.
So two unvetted blogs agreeing stays rumored. Twenty outlets all citing one original report stays rumored, because only the original counts. An official first party announcement jumps straight to confirmed even if it is the only source.
Security rule that lives here too: a source's tier is decided by where the item actually came from in the ingestion pipeline, the verified feed or domain, never by what the article says about itself. Otherwise a page could just claim to be a primary source or a major outlet to inflate its own confidence. That is a direct prompt injection defense and belongs in the security writeup.
Authority versus provenance, resolved: authority lives in the claim's origin, but tier follows verified provenance, the domain the content is actually served from, and the two can come apart. So Tier A means the content itself comes from a verified primary domain (a government site, an official filing system, the company's own verified page, a journal), whether I ingest that feed directly or the agent fetches a primary document cited in a story and checks its domain against the primary allowlist. A secondary outlet reporting a primary action, say Reuters writing that a government ordered something, is Tier B and reaches corroborated on its own, never confirmed, because trusting its claim would mean trusting article text, which the injection defense forbids. It only becomes confirmed if the actual primary document is retrieved and its domain verified. One consistent rule, tier comes from a verified domain, and it gives the agent layer a real job: follow the cited primary and verify it.
5. Display
At a glance (Tier 1) a story shows its category badge, its scale number, and at most one word for confidence state, like rumored, corroborated, or confirmed. The full source count shows up in the Brief and Deep tiers, where the reader has already chosen to go deeper and actually wants the detail. The point is to keep the glance clean and free on the head, and save the counting for when it is wanted.
6. Domain tags
Domain tags (AI/ML, software engineering, cybersecurity, infra, and so on) describe what field a story is in. They are a session level display filter only, a toggle I flip per visit, like show me cybersecurity today. They are never an identity or profile set once at onboarding, and no memory of a preference is kept.
The bright line: domain tags never feed back into category, scale, or confidence. This is what keeps domain filtering from quietly turning into personalized scoring.
•	Open question: can a story carry more than one domain tag, for example a vulnerability in an AI inference framework that is both AI/ML and cybersecurity. Still unresolved, see open questions.
7. Reading tiers
•	Tier 1, Glance: category badge plus one sentence. Fastest possible scan.
•	Tier 2, Brief: Cerix written synthesis, cited, with a thumbnail. The default reading mode.
•	Tier 3, Deep dive: full article, paragraph level images, full citations. For stories worth real time.
•	Tier 4, Surf: relaxed browsing mode for low energy moments. Passive, no decision fatigue.
Tier 2 and up need a generated, cited synthesis, which is RAG backed. Tier 3 needs full text retrieval and citation tracking.
8. Momentum tracking
This is the feature meant to give the reader an actual edge, catching something while it is still small, the I saw this when it was small feeling, instead of finding out once everyone already knows.
A story is not classified once and forgotten. It is tracked as a thread with a history. Momentum is just confidence climbing over time, from rumored to corroborated to confirmed, as independent sources back the story and eventually a primary source closes it. Scale can also move if the underlying facts genuinely change, but the day to day climb is the confidence state moving up.
The critical guardrail: confidence only moves when new independent information arrives, never when engagement or popularity rises. If the trigger were attention based, a quiet but critical story would never get re evaluated, which defeats the whole purpose. A story can climb purely on real corroboration with almost nobody watching, and that is exactly the point.
Worked example
•	Day 1: sources say Company A is in talks to raise 20 billion dollars. Industry Shifting, scale 8 (would be big if true), confidence rumored (1 source).
•	Day 5: multiple independent outlets confirm the talks, term sheet in progress. Still Industry Shifting, scale 8, confidence corroborated (4 independent sources).
•	Day 10: Company A officially announces the raise. Still Industry Shifting, scale 8, confidence confirmed (primary source). It is confirmed because Company A itself announced it, not because the source count went up. One primary source outranks the four secondary ones from Day 5.
Notice scale stays at 8 the whole way, because the size of the thing if true never changed. What climbs is confidence, from rumored to corroborated to confirmed. That is the split doing its job.
9. Dedup
Dedup is now load bearing, not a nice to have. Because confidence leans on a count of independent sources (rumored versus corroborated), the trustworthiness of every confidence value depends on dedup correctly answering one question: is this the same story or a different one. Too loose and unrelated items merge and fake inflate confidence. Too tight and real confirmations never get counted, so confidence stays stuck low.
Linking a new item to an existing thread is standard vector similarity work, nothing novel. The hard part is the similarity threshold, which is still an open question and is now high priority.
Source independence rule: many outlets reprinting the same press release count as one source, not many. Confidence should reflect independent corroboration, not echo. The per item independence judgment that drives confidence (section 4) starts from this same dedup step, since deciding independent versus echo begins with whether two items are the same story.
10. Ingestion and sources
Source selection is still partly open, but one principle is set: pull broadly rather than pulling from a trending or top ranked feed. If ingestion itself only grabbed what was already popular, engagement would quietly decide what Cerix even gets to see, which defeats the thesis. So the candidate set should be the wide feed, not the front page, and impact filtering happens afterwards, on content.
Honest limitation worth writing down: Cerix is strong at this became important and weaker at calling it early, because a genuinely novel claim cannot be verified by anyone at the moment it first appears. Momentum and the confidence state are the honest answer to that. They let a story start low and climb as it earns it, instead of pretending the model can know on day one.
11. System architecture
Stack: Python, FastAPI, Claude API, Chroma for the vector database, Langfuse for evals and tracing.
Build order. Evals matters most, MCP stays intentionally small.
1.	RAG: ingestion, embedding, retrieval. Needed for the cited summaries and for dedup. Everything else depends on it.
2.	Agent tools: mainly confirmation checking, deciding to search and verify something instead of just trusting the source text. The concrete job is following a primary document cited in a story (the actual government order, the company's own page) and verifying its domain against the primary allowlist, which is what can upgrade a story from corroborated to confirmed.
3.	Evals (Langfuse): the layer I should not skip, and it moved ahead of MCP this revision. The whole pitch of Cerix is that it is more consistent and defensible than relevance based scoring, which means nothing without actual measurement. This is also where I deal with calibration drift and hallucination risk. Evals now also has to cover the independence verdicts and the provisional tier assignments for unknown sources, since both silently drive confidence. Evals is the spine.
4.	MCP: kept deliberately small, one real tool. The real job is exposing Cerix itself as an MCP server, so another agent can ask it something like what is the impact score of this story. Built last, and the first thing to cut if the term runs short. It is here for the skill and the interview demo, not because Cerix needs it to work.
5.	Security writeup: threat model, API key handling, prompt injection. An agent reading untrusted news to make scoring calls is a real prompt injection surface, so this is a genuine threat model and not a footnote. One concrete rule lives here: a source's tier is set from verified provenance, the feed or domain the item actually arrived from, not from what the article claims about itself, so a page cannot inflate its own confidence by impersonating a primary source or a major outlet.
Momentum from section 8 gets added after RAG and Agent are working, not built alongside them from day one. The frontend (Streamlit or basic HTML) is for my own daily use. Backend comes first, frontend polish comes later.
12. Storage
Chroma runs in local mode, just writing files to a folder on disk, no separate database server. In development that folder is on my own machine. Once deployed it needs to sit on a persistent disk, not the default temporary container storage that wipes on restart.
Capacity is not a concern at this scale. Even at 100 items a day, that is about 36,000 a year, well under what Chroma handles on a normal machine. So there is no expiration or deletion policy, everything is kept indefinitely, and recency is handled as a display filter only. Targeting the Railway Hobby plan for hosting.
13. Success criteria
Phase 1 is successful if:
•	I open Cerix daily, voluntarily, instead of an engagement driven feed.
•	A spot check of classified items shows me agreeing with the assigned category most of the time, with the exact threshold set during eval design.
•	I can explain every architectural decision and every line of code in an interview without needing to look it up.
•	The two axis output is demonstrably different from what a single score baseline would produce on real stories, see Appendix A.
No growth, revenue, or public adoption metrics apply to Phase 1.
14. Open questions and risks
Resolved this revision (kept here so I remember the decision): the magnitude conflation problem is resolved by splitting into scale plus a confidence state (rumored, corroborated, confirmed) backed by a source count. The source authority gap is resolved by making confirmed a primary source state rather than a count threshold, with primary sources defined in section 4. The rumored to corroborated line and source credibility are resolved too: a source counts toward the state only if it is both independent (model judgment, defaults to echo when unsure) and Tier B or higher, with tiers defined in section 4. The authority versus provenance gap is resolved by tying Tier A to a verified primary domain, reachable either by ingesting the primary feed or by the agent fetching and verifying a cited primary document. Category boundary overlap is resolved by allowing overlap, with Noise exclusive.
•	Dedup similarity threshold: now high priority, because confidence depends on it. How similar is the same story, and where exactly is the line.
•	Domain tag multiplicity: single valued or multi valued, since a story can genuinely span two fields.
•	Momentum trigger sensitivity: independence is now defined in section 4, so what remains open is only the fine tuning, how readily a genuinely new and independent Tier B or higher source should move the state in borderline cases.
•	Source selection (now load bearing): which exact sources to ingest. This stopped being a decide later detail, because confirmed is only reachable when I actually ingest, or can fetch and verify, the relevant primary feeds (the right government sites, official filing systems, company pages). The more primary feeds I cover, the more stories can ever close. High priority, ahead of ingestion design.
•	Hallucination risk: the classifier could confidently assign a wrong category or scale with no signal that it is uncertain. Has to be caught in evals, not patched over later.
•	Noise scope: is quarantined not deleted a UI filter only, or does it need separate storage treatment.
•	Thread current state edge case: a thread shows the latest item's state as current, and dissolves if the item count drops below two.
Appendix A: Worked examples
These were used to pressure test the taxonomy against real and hypothetical cases. They should be expanded into a real labeled eval set once the Evals layer begins.
•	US government forces a lab to block two AI models. Industry Shifting, high scale. Confirmed only if I retrieve and verify the actual order from its own government domain, otherwise corroborated on the strength of the outlets carrying it.
•	Company in talks to raise a large round. Industry Shifting, mid to high scale, low confidence on day one, climbing as it gets confirmed.
•	A major consumer acquisition. Cultural Moment, since it is mainstream relevant rather than an AI industry shift.
•	Niche library 1.0 release. Hot at most, low to mid scale. Relevance tag driven scorers tend to overrate these.
•	Viral essay arguing LLM agents will not scale. Insight, since it is an argument and not an event. Scale reflects argument quality, not discussion volume.
•	Quiet critical security deprecation in a widely used library. Industry Shifting despite near zero discussion. This is the case that proves category cannot depend on attention.

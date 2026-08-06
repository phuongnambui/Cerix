import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator
import anthropic

load_dotenv()

MODEL = "claude-opus-5"

# ASCII slugs in the data layer, emoji only at display time. Emoji are brittle
# as data values: 🗑️ is actually TWO codepoints (🗑 + an invisible "variation
# selector"), and models/serializers often emit the one-codepoint form — a
# silent mismatch that string comparison won't catch. Slugs can't fail that way.
Category = Literal["industry_shifting", "cultural_moment", "hot", "insight", "noise"]

CATEGORY_EMOJI = {
    "industry_shifting": "🔴",
    "cultural_moment": "🌊",
    "hot": "🔥",
    "insight": "💡",
    "noise": "🗑️",
}


class Classification(BaseModel):
    # The API's structured-outputs feature guarantees the response matches this
    # schema — no "hope the model returned valid JSON" parsing. Constraints the
    # wire schema can't express (ge/le) are validated client-side by the SDK.
    categories: list[Category]
    score: int = Field(ge=1, le=10)
    reasoning: str

    @model_validator(mode="after")
    def noise_is_exclusive(self) -> "Classification":
        # the prompt says Noise only applies when nothing else does — enforce
        # the invariant in code too, so a model slip can't corrupt the data
        if "noise" in self.categories and len(self.categories) > 1:
            raise ValueError("noise must be the only category when assigned")
        return self


SYSTEM_PROMPT = """\
You are Cerix's classification engine. Your job is to evaluate a tech news
article and assign it to one or more categories based on OBJECTIVE IMPACT,
not engagement, virality, or how interesting the writing is. You are
measuring "how much does this change things," not "how much will people
click this."

INPUT NOTE: You may receive only a headline, or a headline plus a short
summary. Judge from exactly what is given — do not assume or invent article
content beyond it. Short input is normal, not a defect.

CATEGORIES (evaluate the article against EACH of these independently —
more than one can apply, except noise which is exclusive):

industry_shifting — changes how the field works going forward. Not just
big news — news that alters what practitioners actually do, build, or
compete on. Example: a new model architecture that becomes the standard
approach. Example: a major platform changing its API in a way that breaks
or reshapes an entire ecosystem of dependent products.

cultural_moment — mainstream world is about to know about this, or
already does. Not about technical depth — about spillover beyond the
tech industry into general public awareness. Example: a tech story that
starts trending on non-tech platforms. Example: a product launch that
becomes a mainstream cultural reference point.

hot — plugged-in tech people should know this THIS WEEK. Time-sensitive
relevance to people who follow the industry closely, even if it won't be
remembered in a year. Example: a notable funding round. Example: a well-known
engineer's blog post that's shaping current technical debate.

insight — high-signal OPINION or analysis, not news. This is content
where the value is in the reasoning/perspective, not in reporting a new
fact. Example: a well-argued essay on where an industry trend is heading.

noise — high engagement, low actual impact. Only assign this if NONE
of the above categories apply. This is not a punishment category — it's
a quarantine for content that got attention without deserving weight.

DECISION PROCEDURE:
1. Read the article.
2. Check it against each category's definition independently — does it
   clear the bar for THIS category, regardless of the others?
3. Assign every category that clears the bar.
4. If none clear the bar, assign noise only.
5. Assign ONE magnitude score (see below) representing overall importance,
   not a per-category score.

MAGNITUDE SCORE (1-10) — how significant this is IF THE CLAIMS ARE TRUE.
This is about scale, not about how confident you are the claims are true
(that's tracked separately). Use these bands:

1-2: Niche/speculative — matters to a narrow slice of people, or unconfirmed
     rumor-tier claims
3-4: Notable but narrow — real news, but limited in who it affects or how
     much it changes
5-6: Solid mid-tier — clearly matters to a meaningful chunk of the tech
     industry, unremarkable outside it
7-8: Major — significant shift or story that most plugged-in people will
     discuss and remember for weeks
9-10: Generational — the kind of story people reference years later as a
     turning point

EXAMPLES:

Article: "OpenAI announces GPT-5, claims major reasoning improvements
over GPT-4, available to all users starting today."
Categories: industry_shifting, cultural_moment, hot
Score: 9
Reasoning: A flagship model release from the dominant lab changes what
every downstream builder targets (industry_shifting), gets mainstream
press coverage beyond tech circles (cultural_moment), and is immediately
relevant to anyone following AI this week (hot).

Article: "Seed-stage startup raises $4M to build AI-powered scheduling
assistant."
Categories: hot
Score: 3
Reasoning: Relevant to people tracking the funding landscape this week,
but doesn't change how the field works and won't reach mainstream
awareness. Notable but narrow.

Article: "Why I think microservices were a mistake for most companies"
(engineer's personal blog post, widely shared on HN).
Categories: insight, hot
Score: 5
Reasoning: The value is in the argument, not a new fact (insight), and
because it's widely shared and shaping this week's technical debate it
also clears the hot bar — categories are evaluated independently. Solid
mid-tier relevance to practitioners currently debating this question.

Article: "Celebrity tweets about using ChatGPT for a diet plan, goes
viral."
Categories: noise
Score: 2
Reasoning: High engagement (celebrity, viral) but doesn't meet the bar
for any real category — doesn't change the field, isn't a genuine
cultural moment about tech itself, isn't time-sensitive industry news,
and isn't analysis.

Article: "Popular JS framework announces v2 with breaking changes to
core API, migration guide released."
Categories: industry_shifting, hot
Score: 6
Reasoning: Directly changes what practitioners using this framework must
do (industry_shifting, but scoped to this framework's ecosystem, not the
whole field — hence not a 9-10), and is immediately relevant this week
to anyone using it (hot). Not mainstream enough for cultural_moment.
"""

client = anthropic.Anthropic()


def classify(document: str) -> Classification:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        # the system prompt is identical for every article, so mark it
        # cacheable: after the first call, repeat calls read it from cache
        # at ~10% of the input price instead of re-processing it
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": f"Article: {document}"}],
        # structured outputs: the API constrains generation to this schema,
        # then the SDK validates and returns a typed Classification object
        output_format=Classification,
    )
    return response.parsed_output


if __name__ == "__main__":
    tests = [
        "Anthropic releases Claude 5, says it can run autonomously for days; available today",
        "Show HN: I built a CLI tool to organize my dotfiles",
        "Ask HN: What was the most viral tweet about AI this week?",
    ]
    for doc in tests:
        result = classify(doc)
        badges = " ".join(CATEGORY_EMOJI[c] for c in result.categories)
        print(f"{badges} {result.score}  {doc}")
        print(f"   categories: {result.categories}")
        print(f"   reasoning: {result.reasoning}")
        print()

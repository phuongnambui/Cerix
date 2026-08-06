import spacy

# Pass 2 of dedup: Pass 1 (embedding similarity) says "these two articles are
# ABOUT similar things", but similar topic != same event. Two different AI
# funding rounds read almost identically to an embedding model. Named entities
# (the specific people/companies/places involved) are what distinguish "same
# event" from "same genre of event".

# Entity types we keep, and why each one matters for news dedup:
#   PERSON      — people ("Sam Altman", "Linus Torvalds"). Same story = same actors.
#   ORG         — companies, agencies, teams ("OpenAI", "EU Commission").
#   GPE         — geo-political entities: countries, cities, states ("China",
#                 "California"). Catches regulation/policy stories tied to a place.
#   PRODUCT     — named products ("iPhone", "ChatGPT"). Launch/recall stories
#                 hinge on WHICH product.
#   WORK_OF_ART — titles of creative works, papers, books ("Attention Is All
#                 You Need"). Research-paper stories are keyed on the paper name.
# Types we deliberately DROP: DATE, TIME, CARDINAL, MONEY, PERCENT etc. —
# "Tuesday" and "$10 million" appear in thousands of unrelated stories and
# would create false entity matches.
RELEVANT_ENTITY_TYPES = {"PERSON", "ORG", "GPE", "PRODUCT", "WORK_OF_ART"}

# how many entities two articles must share to be called the same event.
# 1 is deliberately loose for now (our texts are short — often just a title,
# so entity sets are tiny); raise it once articles have full body text.
MIN_ENTITY_OVERLAP = 1

# loaded once at import time, not per call — model load is the slow part
# (like opening one DB connection at server start instead of per request)
nlp = spacy.load("en_core_web_sm")


def extract_entities(text: str) -> set[str]:
    # nlp(text) runs spaCy's full pipeline (tokenize -> tag -> NER) and
    # returns a Doc; doc.ents is every named entity span it found
    doc = nlp(text)
    return {
        # lowercase so "OpenAI" and "openai" count as the same entity —
        # set membership is exact string match, casing would split them
        ent.text.lower()
        for ent in doc.ents
        if ent.label_ in RELEVANT_ENTITY_TYPES
    }


def is_confirmed_duplicate(article_a_text: str, article_b_text: str) -> bool:
    entities_a = extract_entities(article_a_text)
    entities_b = extract_entities(article_b_text)

    # set intersection: entities that appear in BOTH articles
    shared = entities_a & entities_b
    return len(shared) >= MIN_ENTITY_OVERLAP


if __name__ == "__main__":
    # same event, different wording — should be a confirmed duplicate
    a = "OpenAI announces GPT-5, its most capable model yet, says Sam Altman."
    b = "Sam Altman unveils GPT-5 in a livestream from OpenAI headquarters."
    # same topic (AI model launch), different event — should be rejected
    c = "Google DeepMind releases Gemini 3 with improved reasoning."

    print("a entities:", extract_entities(a))
    print("b entities:", extract_entities(b))
    print("c entities:", extract_entities(c))
    print("a vs b (same event):     ", is_confirmed_duplicate(a, b))
    print("a vs c (different event):", is_confirmed_duplicate(a, c))

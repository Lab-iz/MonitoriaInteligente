from collections import Counter

from app.models import Discipline, KnowledgeBaseItem, Topic


def _tokenize(value):
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in (value or ""))
    return {token for token in cleaned.split() if len(token) > 2}


def search_related_items(ticket=None, discipline_id=None, topic_id=None, query_text="", limit=5):
    if ticket is not None:
        discipline_id = ticket.discipline_id
        topic_id = ticket.topic_id
        query_text = " ".join(
            [ticket.title or "", ticket.description or "", ticket.prior_attempt or ""]
        )

    if not discipline_id:
        return []

    items = KnowledgeBaseItem.query.filter_by(discipline_id=discipline_id, active=True).all()
    keywords = _tokenize(query_text)
    ranked = []

    for item in items:
        score = 1
        if item.validated:
            score += 3
        if item.official:
            score += 2
        if topic_id and item.topic_id == topic_id:
            score += 4

        item_tokens = _tokenize(" ".join([item.title, item.content, item.tags or ""]))
        score += len(keywords.intersection(item_tokens)) * 2
        ranked.append((score, item))

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in ranked if score > 1][:limit]


def topic_frequency_for_discipline(discipline_id):
    discipline = Discipline.query.get(discipline_id)
    counter = Counter()
    if not discipline:
        return []

    for topic in discipline.topics:
        counter[topic.name] = len(topic.tickets)

    return [{"label": topic, "value": total} for topic, total in counter.most_common()]


def get_disciplines_and_topics():
    disciplines = Discipline.query.order_by(Discipline.name).all()
    topics = Topic.query.order_by(Topic.name).all()
    return disciplines, topics

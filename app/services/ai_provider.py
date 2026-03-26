from dataclasses import dataclass


def _tokenize(value):
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in (value or ""))
    return {token for token in cleaned.split() if len(token) > 2}


@dataclass
class TriageResult:
    classification: str
    summary: str
    suggested_response: str
    refinement_questions: str
    related_materials: str
    confidence: float
    low_confidence: bool
    provider_name: str = "mock"


class BaseAIProvider:
    provider_name = "base"

    def generate_ticket_triage(self, ticket, related_items):
        raise NotImplementedError


class MockAIProvider(BaseAIProvider):
    provider_name = "mock"

    def generate_ticket_triage(self, ticket, related_items):
        keywords = _tokenize(
            " ".join([ticket.title or "", ticket.description or "", ticket.prior_attempt or ""])
        )
        confidence = 0.42
        if ticket.topic:
            confidence += 0.12
        if ticket.prior_attempt:
            confidence += 0.08
        if len(keywords) >= 8:
            confidence += 0.08
        if related_items:
            confidence += min(len(related_items), 3) * 0.08
        if ticket.urgency == "critica":
            confidence -= 0.05

        confidence = max(0.2, min(confidence, 0.92))
        low_confidence = confidence < 0.58 or len(ticket.description or "") < 60

        classification = (
            f"{ticket.discipline.name} > {ticket.topic.name} > {ticket.question_type.title()}"
        )
        summary = (
            f"Estudante relata dúvida '{ticket.title}' em {ticket.topic.name}, "
            f"com urgência {ticket.urgency}. "
            f"Tentativa prévia: {'sim' if ticket.prior_attempt else 'não informada'}."
        )

        references = [f"- {item.title}" for item in related_items[:3]]
        related_materials = "\n".join(references) if references else "- Nenhum item fortemente relacionado foi encontrado."

        suggested_response = (
            "Sugestão automática de pré-atendimento:\n"
            f"1. Releia o enunciado destacando o ponto central ligado a {ticket.topic.name}.\n"
            "2. Compare sua tentativa com o procedimento conceitual esperado.\n"
            "3. Se houver erro de interpretação, isole a etapa em que a dúvida começa.\n"
            "4. Consulte os materiais relacionados antes de escalar para atendimento humano."
        )

        if ticket.question_type == "codigo":
            suggested_response += (
                "\n5. Valide entradas, saídas e estruturas de repetição usadas no trecho de código."
            )
        elif ticket.question_type in {"prova", "tarefa", "trabalho"}:
            suggested_response += (
                "\n5. Priorize os tópicos cobrados e organize uma sequência curta de revisão."
            )

        refinement_questions = (
            "Perguntas de refinamento sugeridas:\n"
            "- Em qual etapa específica a dúvida aparece?\n"
            "- O que você já tentou e qual foi o resultado?\n"
            "- Há um enunciado, imagem ou código que ajude a contextualizar?"
        )

        return TriageResult(
            classification=classification,
            summary=summary,
            suggested_response=suggested_response,
            refinement_questions=refinement_questions,
            related_materials=related_materials,
            confidence=confidence,
            low_confidence=low_confidence,
            provider_name=self.provider_name,
        )


def get_ai_provider(provider_name="mock"):
    return MockAIProvider()

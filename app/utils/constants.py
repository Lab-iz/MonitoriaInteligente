USER_ROLES = [
    ("student", "Estudante"),
    ("monitor", "Monitor"),
    ("teacher", "Professor"),
    ("admin", "Pedagógico/Admin"),
]

QUESTION_TYPES = [
    ("conceitual", "Conceitual"),
    ("exercicio", "Exercício"),
    ("codigo", "Código"),
    ("interpretacao", "Interpretação"),
    ("tarefa", "Tarefa"),
    ("prova", "Prova"),
    ("trabalho", "Trabalho"),
]

URGENCY_LEVELS = [
    ("baixa", "Baixa"),
    ("media", "Média"),
    ("alta", "Alta"),
    ("critica", "Crítica"),
]

TICKET_STATUSES = [
    ("aberta", "Aberta"),
    ("triada_ia", "Triada por IA"),
    ("aguardando_monitor", "Aguardando monitor"),
    ("em_atendimento", "Em atendimento"),
    ("respondida", "Respondida"),
    ("parcialmente_resolvida", "Parcialmente resolvida"),
    ("resolvida", "Resolvida"),
    ("encaminhada_professor", "Encaminhada ao professor"),
    ("arquivada", "Arquivada"),
]

INTERVENTION_TYPES = [
    ("orientacao", "Orientação"),
    ("explicacao", "Explicação conceitual"),
    ("revisao_codigo", "Revisão de código"),
    ("encaminhamento", "Encaminhamento"),
    ("recomendacao_material", "Recomendação de material"),
]

RISK_LEVELS = [
    ("baixo", "Baixo"),
    ("moderado", "Moderado"),
    ("alto", "Alto"),
]


def label_from(choices, value, default=None):
    mapping = dict(choices)
    return mapping.get(value, default or value)

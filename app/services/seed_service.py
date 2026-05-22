from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import (
    ClassGroup,
    Course,
    Discipline,
    DisciplineMembership,
    KnowledgeBaseItem,
    MonitorShift,
    MonitorTopic,
    QuestionTicket,
    Topic,
    User,
)
from app.services.feedback_service import save_feedback
from app.services.ticket_service import generate_ticket_number, register_monitor_response
from app.services.triage_service import run_initial_triage
from app.utils.time import utcnow


def _create_user(full_name, username, email, role, phone=None):
    user = User(full_name=full_name, username=username, email=email, role=role, phone=phone)
    user.set_password(current_app.config["SEED_DEFAULT_PASSWORD"])
    db.session.add(user)
    return user


def seed_demo_data():
    if User.query.first():
        return

    engenharia = Course(code="BCC", name="Bacharelado em Ciência da Computação")
    licenciatura = Course(code="MAT", name="Licenciatura em Matemática")
    db.session.add_all([engenharia, licenciatura])
    db.session.flush()

    turma_a = ClassGroup(course=engenharia, name="Turma A", semester_label="2026.1")
    turma_b = ClassGroup(course=licenciatura, name="Turma B", semester_label="2026.1")
    db.session.add_all([turma_a, turma_b])
    db.session.flush()

    algoritmos = Discipline(course=engenharia, code="COMP101", name="Algoritmos")
    estruturas = Discipline(course=engenharia, code="COMP201", name="Estruturas de Dados")
    calculo = Discipline(course=licenciatura, code="MAT101", name="Cálculo I")
    db.session.add_all([algoritmos, estruturas, calculo])
    db.session.flush()

    topicos = {
        "variaveis": Topic(discipline=algoritmos, name="Variáveis e Tipos", criticality=2),
        "repeticao": Topic(discipline=algoritmos, name="Estruturas de Repetição", criticality=3),
        "lista": Topic(discipline=estruturas, name="Listas Encadeadas", criticality=3),
        "pilha": Topic(discipline=estruturas, name="Pilhas e Filas", criticality=2),
        "limite": Topic(discipline=calculo, name="Limites", criticality=3),
        "derivada": Topic(discipline=calculo, name="Derivadas", criticality=3),
    }
    db.session.add_all(topicos.values())

    admin = _create_user("Coordenação Pedagógica", "admin", "admin@monitoria.local", "admin")
    professor_algo = _create_user("Prof. Helena Ramos", "helena", "helena@monitoria.local", "teacher")
    professor_calc = _create_user("Prof. Caio Nunes", "caio", "caio@monitoria.local", "teacher")
    monitor_lia = _create_user("Lia Monteiro", "lia", "lia@monitoria.local", "monitor", "(11) 90000-0101")
    monitor_otavio = _create_user("Otávio Braga", "otavio", "otavio@monitoria.local", "monitor", "(11) 90000-0202")
    estudante_ana = _create_user("Ana Souza", "ana", "ana@monitoria.local", "student")
    estudante_bruno = _create_user("Bruno Lima", "bruno", "bruno@monitoria.local", "student")
    estudante_clara = _create_user("Clara Reis", "clara", "clara@monitoria.local", "student")
    db.session.flush()

    memberships = [
        DisciplineMembership(user=professor_algo, discipline=algoritmos, class_group=turma_a, relationship_type="teacher"),
        DisciplineMembership(user=professor_algo, discipline=estruturas, class_group=turma_a, relationship_type="teacher"),
        DisciplineMembership(user=professor_calc, discipline=calculo, class_group=turma_b, relationship_type="teacher"),
        DisciplineMembership(user=monitor_lia, discipline=algoritmos, class_group=turma_a, relationship_type="monitor"),
        DisciplineMembership(user=monitor_otavio, discipline=estruturas, class_group=turma_a, relationship_type="monitor"),
        DisciplineMembership(user=monitor_otavio, discipline=calculo, class_group=turma_b, relationship_type="monitor"),
        DisciplineMembership(user=estudante_ana, discipline=algoritmos, class_group=turma_a, relationship_type="student"),
        DisciplineMembership(user=estudante_ana, discipline=estruturas, class_group=turma_a, relationship_type="student"),
        DisciplineMembership(user=estudante_bruno, discipline=algoritmos, class_group=turma_a, relationship_type="student"),
        DisciplineMembership(user=estudante_bruno, discipline=calculo, class_group=turma_b, relationship_type="student"),
        DisciplineMembership(user=estudante_clara, discipline=estruturas, class_group=turma_a, relationship_type="student"),
    ]
    db.session.add_all(memberships)

    monitor_topics = [
        MonitorTopic(monitor=monitor_lia, topic=topicos["variaveis"]),
        MonitorTopic(monitor=monitor_lia, topic=topicos["repeticao"]),
        MonitorTopic(monitor=monitor_otavio, topic=topicos["lista"]),
        MonitorTopic(monitor=monitor_otavio, topic=topicos["pilha"]),
        MonitorTopic(monitor=monitor_otavio, topic=topicos["limite"]),
        MonitorTopic(monitor=monitor_otavio, topic=topicos["derivada"]),
    ]
    db.session.add_all(monitor_topics)

    kb_items = [
        KnowledgeBaseItem(
            discipline=algoritmos,
            topic=topicos["repeticao"],
            title="Guia oficial de while e for",
            content="Explicação passo a passo com exemplos de repetição controlada por contador e condição.",
            item_type="roteiro",
            tags="laço,for,while,repetição",
            official=True,
            validated=True,
            validated_by=professor_algo,
            validated_at=utcnow(),
        ),
        KnowledgeBaseItem(
            discipline=algoritmos,
            topic=topicos["variaveis"],
            title="Erros comuns de conversão de tipos",
            content="Checklist para validar entrada, casting e impressão de valores.",
            item_type="faq_validada",
            tags="tipos,casting,input",
            official=False,
            validated=True,
            validated_by=professor_algo,
            validated_at=utcnow(),
        ),
        KnowledgeBaseItem(
            discipline=estruturas,
            topic=topicos["lista"],
            title="Lista encadeada: inserção no início",
            content="Resumo com ponteiros, referência para o próximo nó e exemplo em Python.",
            item_type="pdf",
            tags="lista,nó,ponteiro,python",
            official=True,
            validated=False,
            suggested_by=monitor_otavio,
        ),
        KnowledgeBaseItem(
            discipline=calculo,
            topic=topicos["limite"],
            title="Limites fundamentais",
            content="Roteiro de estudo com interpretação gráfica e exercícios resolvidos.",
            item_type="video",
            tags="limite,continuidade,gráfico",
            official=True,
            validated=True,
            validated_by=professor_calc,
            validated_at=utcnow(),
        ),
    ]
    db.session.add_all(kb_items)

    shifts = [
        MonitorShift(
            monitor=monitor_lia,
            discipline=algoritmos,
            class_group=turma_a,
            title="Plantão de Algoritmos",
            start_at=utcnow() + timedelta(days=1, hours=2),
            end_at=utcnow() + timedelta(days=1, hours=4),
            location="Laboratório 3",
            notes="Foco em estruturas de repetição e depuração.",
        ),
        MonitorShift(
            monitor=monitor_otavio,
            discipline=estruturas,
            class_group=turma_a,
            title="Plantão de Estruturas",
            start_at=utcnow() + timedelta(days=2, hours=1),
            end_at=utcnow() + timedelta(days=2, hours=3),
            location="Sala híbrida",
            notes="Atendimento para listas e pilhas.",
        ),
        MonitorShift(
            monitor=monitor_otavio,
            discipline=calculo,
            class_group=turma_b,
            title="Plantão de Cálculo I",
            start_at=utcnow() + timedelta(days=3, hours=2),
            end_at=utcnow() + timedelta(days=3, hours=4),
            location="Meet institucional",
            notes="Revisão de limites antes da avaliação.",
        ),
    ]
    db.session.add_all(shifts)
    db.session.flush()

    tickets = [
        QuestionTicket(
            ticket_number=generate_ticket_number(),
            student=estudante_ana,
            discipline=algoritmos,
            topic=topicos["repeticao"],
            class_group=turma_a,
            title="Não consigo entender a diferença entre while e for",
            description="Estou travada na lista 2 porque não sei quando usar while e quando usar for.",
            question_type="conceitual",
            urgency="media",
            prior_attempt="Li os slides e tentei fazer o exercício 3.",
        ),
        QuestionTicket(
            ticket_number=generate_ticket_number(),
            student=estudante_bruno,
            discipline=calculo,
            topic=topicos["limite"],
            class_group=turma_b,
            title="Limite lateral na prova de amanhã",
            description="Tenho dificuldade para identificar quando o limite lateral diverge e a prova é amanhã.",
            question_type="prova",
            urgency="alta",
            deadline=utcnow() + timedelta(days=1),
            prior_attempt="Refiz dois exercícios da lista.",
        ),
        QuestionTicket(
            ticket_number=generate_ticket_number(),
            student=estudante_clara,
            discipline=estruturas,
            topic=topicos["lista"],
            class_group=turma_a,
            title="Meu código de lista encadeada entra em loop infinito",
            description="Ao inserir um nó no início, a impressão da lista fica infinita e não localizei o erro.",
            question_type="codigo",
            urgency="alta",
            prior_attempt="Testei com print em cada nó, mas continuo perdida.",
        ),
    ]
    db.session.add_all(tickets)
    db.session.flush()

    for ticket in tickets:
        run_initial_triage(ticket, actor=admin)

    tickets[0].ai_helpful = True
    tickets[0].status = "respondida"
    register_monitor_response(
        tickets[0],
        monitor_lia,
        {
            "body": "Use `for` quando souber a quantidade de repetições e `while` quando a condição definir a parada. No seu exercício, conte quantas leituras precisam acontecer.",
            "intervention_type": "explicacao",
            "recommended_materials": "Guia oficial de while e for",
            "pedagogical_notes": "A estudante entende a lógica quando vê um quadro comparativo.",
            "duration_minutes": "18",
            "status_after": "resolvida",
        },
    )

    register_monitor_response(
        tickets[2],
        monitor_otavio,
        {
            "body": "O loop infinito provavelmente vem da atualização incorreta do ponteiro `next`. Revise a ordem de atribuição ao inserir o nó.",
            "intervention_type": "revisao_codigo",
            "recommended_materials": "Lista encadeada: inserção no início",
            "pedagogical_notes": "Precisa reforçar rastreamento manual de ponteiros.",
            "duration_minutes": "25",
            "status_after": "parcialmente_resolvida",
        },
    )

    save_feedback(
        tickets[0],
        estudante_ana,
        {
            "ai_helpful": "sim",
            "monitor_rating": "5",
            "resolved": "sim",
            "comment": "A comparação entre while e for ajudou bastante.",
        },
    )

    db.session.commit()

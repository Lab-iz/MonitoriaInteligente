from app.extensions import db
from app.models import DisciplineMembership, MonitorTopic, QuestionTicket, User


def test_login_flow(client):
    response = client.post(
        "/auth/login",
        data={"username": "ana", "password": "demo123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Seu acompanhamento academico" in response.data or b"Seu acompanhamento acad" in response.data


def test_student_cannot_access_admin_dashboard(client):
    client.post(
        "/auth/login",
        data={"username": "ana", "password": "demo123"},
        follow_redirects=True,
    )
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/student/dashboard" in response.headers["Location"]


def test_create_ticket_runs_triage(app, client):
    client.post(
        "/auth/login",
        data={"username": "ana", "password": "demo123"},
        follow_redirects=True,
    )
    response = client.post(
        "/tickets/new",
        data={
            "course_id": "1",
            "discipline_id": "1",
            "topic_id": "2",
            "class_group_id": "1",
            "title": "Teste de triagem",
            "description": "Preciso de ajuda para entender um laço while em um exercício de repetição.",
            "question_type": "conceitual",
            "urgency": "media",
            "deadline": "",
            "prior_attempt": "Li os slides e tentei fazer o exercício.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        ticket = QuestionTicket.query.filter_by(title="Teste de triagem").first()
        assert ticket is not None
        assert ticket.ai_suggestion is not None
        assert ticket.status in {"triada_ia", "aguardando_monitor"}


def test_request_human_support_moves_ticket_to_queue(app, client):
    client.post(
        "/auth/login",
        data={"username": "ana", "password": "demo123"},
        follow_redirects=True,
    )
    client.post(
        "/tickets/new",
        data={
            "course_id": "1",
            "discipline_id": "1",
            "topic_id": "2",
            "class_group_id": "1",
            "title": "Quero atendimento humano",
            "description": "A resposta inicial nao foi suficiente e preciso de apoio do monitor.",
            "question_type": "conceitual",
            "urgency": "alta",
            "deadline": "",
            "prior_attempt": "Tentei refazer a lista sozinho.",
        },
        follow_redirects=True,
    )

    with app.app_context():
        ticket = QuestionTicket.query.filter_by(title="Quero atendimento humano").first()
        ticket_id = ticket.id

    response = client.post(f"/tickets/{ticket_id}/request-human", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        ticket = db.session.get(QuestionTicket, ticket_id)
        assert ticket.status == "aguardando_monitor"


def test_monitor_registration_records_topics_and_phone(app, client):
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Marina Silva",
            "username": "marina",
            "email": "marina@monitoria.local",
            "role": "monitor",
            "password": "demo123",
            "phone": "(11) 90000-0303",
            "topic_ids": ["1", "2"],
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username="marina").first()
        assert user is not None
        assert user.phone == "(11) 90000-0303"
        assert {capability.topic_id for capability in user.monitor_topics} == {1, 2}
        assert {
            membership.discipline_id
            for membership in user.memberships
            if membership.relationship_type == "monitor"
        } == {1}


def test_student_can_choose_another_monitor(app, client):
    with app.app_context():
        monitor = User(
            full_name="Pedro Monitor",
            username="pedro_monitor",
            email="pedro@monitoria.local",
            role="monitor",
            phone="(11) 90000-0404",
        )
        monitor.set_password("demo123")
        db.session.add(monitor)
        db.session.flush()
        db.session.add(
            DisciplineMembership(
                user=monitor,
                discipline_id=1,
                relationship_type="monitor",
            )
        )
        db.session.add(MonitorTopic(monitor=monitor, topic_id=2))
        ticket = QuestionTicket.query.filter_by(
            title="Não consigo entender a diferença entre while e for"
        ).first()
        ticket_id = ticket.id
        monitor_id = monitor.id
        db.session.commit()

    client.post(
        "/auth/login",
        data={"username": "ana", "password": "demo123"},
        follow_redirects=True,
    )
    response = client.post(
        f"/tickets/{ticket_id}/choose-monitor",
        data={"monitor_id": str(monitor_id)},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        updated = db.session.get(QuestionTicket, ticket_id)
        assert updated.assigned_monitor_id == monitor_id
        assert updated.status == "aguardando_monitor"


def test_monitor_can_answer_ticket(app, client):
    with app.app_context():
        ticket = QuestionTicket.query.filter_by(title="Meu código de lista encadeada entra em loop infinito").first()
        ticket_id = ticket.id

    client.post(
        "/auth/login",
        data={"username": "otavio", "password": "demo123"},
        follow_redirects=True,
    )
    response = client.post(
        f"/tickets/{ticket_id}/respond",
        data={
            "body": "Revise a atualizacao do ponteiro next antes de percorrer a estrutura.",
            "intervention_type": "revisao_codigo",
            "recommended_materials": "Lista encadeada: insercao no inicio",
            "pedagogical_notes": "Precisa reforcar rastreamento manual.",
            "duration_minutes": "20",
            "status_after": "resolvida",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        updated = db.session.get(QuestionTicket, ticket_id)
        assert updated.status == "resolvida"
        assert updated.human_responses[-1].body.startswith("Revise")


def test_teacher_can_answer_ticket(app, client):
    with app.app_context():
        ticket = QuestionTicket.query.filter_by(title="Limite lateral na prova de amanhã").first()
        ticket_id = ticket.id

    client.post(
        "/auth/login",
        data={"username": "caio", "password": "demo123"},
        follow_redirects=True,
    )
    response = client.post(
        f"/tickets/{ticket_id}/respond",
        data={
            "body": "Vamos revisar os limites laterais e registrar os casos de divergência.",
            "intervention_type": "explicacao",
            "recommended_materials": "Roteiro de limites fundamentais",
            "pedagogical_notes": "Aluno precisa comparar sinais nos dois lados.",
            "duration_minutes": "30",
            "status_after": "respondida",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        updated = db.session.get(QuestionTicket, ticket_id)
        assert updated.status == "respondida"
        assert updated.human_responses[-1].responder.username == "caio"


def test_monitor_queue_filters_by_course(client):
    client.post(
        "/auth/login",
        data={"username": "lia", "password": "demo123"},
        follow_redirects=True,
    )
    response = client.get("/tickets/queue?course_id=1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Algoritmos" in response.data
    assert b"Estruturas de Dados" not in response.data


def test_report_export_returns_csv(client):
    client.post(
        "/auth/login",
        data={"username": "admin", "password": "demo123"},
        follow_redirects=True,
    )
    response = client.get("/reports/export/disciplinas")
    assert response.status_code == 200
    assert "text/csv" in response.headers["Content-Type"]

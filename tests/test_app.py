from app.extensions import db
from app.models import QuestionTicket


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

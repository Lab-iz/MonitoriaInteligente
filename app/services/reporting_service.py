import csv
from datetime import datetime
from pathlib import Path

from flask import current_app
from sqlalchemy import case, func

from app.extensions import db
from app.models import Discipline, QuestionTicket, ReportSnapshot, User
from app.utils.time import utcnow


REPORT_LABELS = {
    "disciplinas": "Dúvidas por disciplina",
    "temas": "Dúvidas por tema",
    "alunos": "Histórico por aluno",
    "monitoria": "Desempenho da monitoria",
    "ia": "Efetividade da triagem por IA",
}


def build_rows(report_type):
    if report_type == "disciplinas":
        rows = (
            db.session.query(
                Discipline.name.label("disciplina"),
                func.count(QuestionTicket.id).label("duvidas"),
                func.avg(QuestionTicket.priority_score).label("prioridade_media"),
            )
            .join(QuestionTicket, QuestionTicket.discipline_id == Discipline.id)
            .group_by(Discipline.name)
            .all()
        )
        return [
            {
                "disciplina": row.disciplina,
                "duvidas": row.duvidas,
                "prioridade_media": round(float(row.prioridade_media or 0), 2),
            }
            for row in rows
        ]

    if report_type == "alunos":
        rows = (
            db.session.query(
                User.full_name.label("aluno"),
                func.count(QuestionTicket.id).label("duvidas"),
                func.sum(case((QuestionTicket.status == "resolvida", 1), else_=0)).label("resolvidas"),
            )
            .join(QuestionTicket, QuestionTicket.student_id == User.id)
            .filter(User.role == "student")
            .group_by(User.full_name)
            .all()
        )
        return [
            {"aluno": row.aluno, "duvidas": row.duvidas, "resolvidas": row.resolvidas or 0}
            for row in rows
        ]

    if report_type == "ia":
        rows = QuestionTicket.query.order_by(QuestionTicket.created_at.desc()).all()
        return [
            {
                "ticket": row.ticket_number,
                "disciplina": row.discipline.name,
                "status": row.status,
                "confianca_ia": row.ai_confidence,
                "util_ao_aluno": row.ai_helpful,
            }
            for row in rows
        ]

    rows = QuestionTicket.query.order_by(QuestionTicket.created_at.desc()).all()
    return [
        {
            "ticket": row.ticket_number,
            "disciplina": row.discipline.name,
            "tema": row.topic.name,
            "aluno": row.student.full_name,
            "status": row.status,
            "urgencia": row.urgency,
        }
        for row in rows
    ]


def generate_csv_report(report_type, generated_by):
    rows = build_rows(report_type)
    report_dir = Path(current_app.config["REPORT_FOLDER"])
    report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{report_type}_{utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path = report_dir / filename

    fieldnames = list(rows[0].keys()) if rows else ["sem_dados"]
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)
        else:
            writer.writerow({"sem_dados": "Nenhum dado encontrado"})

    snapshot = ReportSnapshot(
        name=REPORT_LABELS.get(report_type, report_type),
        report_type=report_type,
        generated_by=generated_by,
        filters_json={},
        csv_path=str(csv_path),
    )
    db.session.add(snapshot)
    db.session.commit()
    return snapshot

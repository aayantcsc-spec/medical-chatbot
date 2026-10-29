"""
export.py

Builds the three export formats requested for a completed evaluation
run (spec item 19): CSV, Excel, and a PDF report. Every number in
every export comes directly from the database (evaluation_results /
evaluation_runs / user_study_responses) for the given run_id -- this
file never invents data, and if a run has no results it raises
instead of producing an empty-looking "successful" report.

Excel export uses openpyxl, PDF export uses reportlab. Both are
listed in requirements.txt. If either package is missing in a given
environment, the corresponding function raises ImportError with a
clear message rather than silently failing.
"""

import csv
import io
from datetime import datetime

from database import database as db
from evaluation.chatbot_adapter import CHATBOT_NAMES
from evaluation.metrics import summarize_results, compute_overall_scores, OVERALL_SCORE_WEIGHTS


class ExportError(Exception):
    pass


def _load_run_data(run_id):
    run = db.get_evaluation_run(run_id)
    if run is None:
        raise ExportError(f"Evaluation run {run_id} was not found.")

    results = db.get_evaluation_results(run_id)
    if not results:
        raise ExportError(f"Evaluation run {run_id} has no stored results to export.")

    bot_summary = summarize_results(results)
    user_study_averages_raw = db.get_user_study_averages()
    user_study_avg_overall = {
        name: info["avg_overall"] for name, info in user_study_averages_raw.items()
    }
    scored, ranking = compute_overall_scores(bot_summary, user_study_avg_overall)

    return run, results, scored, ranking, user_study_averages_raw


# ============================================================
# CSV EXPORT (raw per-question results)
# ============================================================

def export_csv(run_id):
    run, results, scored, ranking, _ = _load_run_data(run_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "question_id", "category", "chatbot_name", "question", "response",
        "response_time_ms", "correctness_score", "keyword_score", "intent_score",
        "semantic_score", "safety_score", "safety_level", "overall_quality_score",
        "is_error", "error_message",
    ])

    for row in results:
        writer.writerow([
            row["question_id"], row["category"], row["chatbot_name"], row["question"],
            row["response"], row["response_time_ms"], row["correctness_score"],
            row["keyword_score"], row["intent_score"], row["semantic_score"],
            row["safety_score"], row["safety_level"], row["overall_quality_score"],
            row["is_error"], row["error_message"],
        ])

    return buffer.getvalue().encode("utf-8")


# ============================================================
# EXCEL EXPORT
# ============================================================

def export_excel(run_id):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError as error:
        raise ExportError(
            "Excel export requires the 'openpyxl' package. Install it with "
            "'pip install openpyxl'."
        ) from error

    run, results, scored, ranking, user_study_averages_raw = _load_run_data(run_id)

    workbook = Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="3A5A40", end_color="3A5A40", fill_type="solid")

    # ---- Sheet 1: Comparison summary ----
    summary_sheet = workbook.active
    summary_sheet.title = "Comparison Summary"
    headers = ["Chatbot", "Accuracy (%)", "Avg Response Time (ms)",
               "Avg Safety Score", "Avg Quality Score", "Overall Score", "Rank"]
    summary_sheet.append(headers)
    for cell in summary_sheet[1]:
        cell.font = header_font
        cell.fill = header_fill

    rank_by_name = {row["chatbot_name"]: i + 1 for i, row in enumerate(ranking)}

    for name in CHATBOT_NAMES:
        s = scored.get(name)
        if s is None:
            summary_sheet.append([name, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
            continue
        summary_sheet.append([
            name, s["accuracy"], s["avg_response_time_ms"], s["avg_safety_score"],
            s["avg_quality_score"], s["overall_score"], rank_by_name.get(name, "N/A"),
        ])

    # ---- Sheet 2: Raw results ----
    raw_sheet = workbook.create_sheet("Raw Results")
    raw_headers = [
        "question_id", "category", "chatbot_name", "question", "response",
        "response_time_ms", "correctness_score", "safety_score", "safety_level",
        "overall_quality_score", "is_error", "error_message",
    ]
    raw_sheet.append(raw_headers)
    for cell in raw_sheet[1]:
        cell.font = header_font
        cell.fill = header_fill

    for row in results:
        raw_sheet.append([
            row["question_id"], row["category"], row["chatbot_name"], row["question"],
            row["response"], row["response_time_ms"], row["correctness_score"],
            row["safety_score"], row["safety_level"], row["overall_quality_score"],
            row["is_error"], row["error_message"],
        ])

    # ---- Sheet 3: User study ----
    study_sheet = workbook.create_sheet("User Study")
    study_sheet.append(["Chatbot", "Avg Accuracy", "Avg Clarity", "Avg Trust", "Avg Overall", "Responses"])
    for cell in study_sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
    for name in CHATBOT_NAMES:
        info = user_study_averages_raw.get(name)
        if info:
            study_sheet.append([
                name, info["avg_accuracy"], info["avg_clarity"],
                info["avg_trust"], info["avg_overall"], info["response_count"],
            ])
        else:
            study_sheet.append([name, "N/A", "N/A", "N/A", "N/A", 0])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# ============================================================
# PDF REPORT EXPORT
# ============================================================

def export_pdf(run_id):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
    except ImportError as error:
        raise ExportError(
            "PDF export requires the 'reportlab' package. Install it with "
            "'pip install reportlab'."
        ) from error

    run, results, scored, ranking, user_study_averages_raw = _load_run_data(run_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleGreen", parent=styles["Title"], textColor=colors.HexColor("#3A5A40"))
    heading_style = ParagraphStyle("HeadingGreen", parent=styles["Heading2"], textColor=colors.HexColor("#588157"))

    story = []

    # ---- 1. Experiment information ----
    story.append(Paragraph("MediChat Comparative Evaluation Report", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "MediChat is an educational AI system designed for healthcare information "
        "and chatbot architecture evaluation. It does not provide a medical diagnosis "
        "or replace a qualified healthcare professional.",
        styles["Italic"],
    ))
    story.append(Spacer(1, 12))

    info_table = Table([
        ["Run ID", str(run["id"])],
        ["Run Label", run["run_label"] or "-"],
        ["Status", run["status"]],
        ["Started", str(run["started_at"])],
        ["Completed", str(run["completed_at"] or "-")],
        ["Total Questions", str(run["total_questions"])],
        ["Total Architectures", str(run["total_chatbots"])],
        ["Total Responses Evaluated", str(run["total_responses"])],
        ["Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ], colWidths=[6 * cm, 9 * cm])
    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A3B18A")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#DAD7CD")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    # ---- 2 & 3. Dataset and architectures ----
    story.append(Paragraph("Dataset & Architectures", heading_style))
    story.append(Paragraph(
        f"Questions used: datasets/evaluation_questions.csv "
        f"({run['total_questions']} healthcare questions across multiple categories: "
        "general health, respiratory, digestive, cardiac, musculoskeletal, chronic "
        "disease, medication safety, prevention, and emergency).",
        styles["Normal"],
    ))
    story.append(Paragraph(
        "Architectures evaluated: " + ", ".join(CHATBOT_NAMES) + ".",
        styles["Normal"],
    ))
    story.append(Spacer(1, 16))

    # ---- 4-7. Comparison table ----
    story.append(Paragraph("Accuracy / Speed / Safety / Quality Comparison", heading_style))

    table_data = [["Chatbot", "Accuracy (%)", "Avg Time (ms)", "Safety", "Quality", "Overall"]]
    for name in CHATBOT_NAMES:
        s = scored.get(name)
        if s is None:
            table_data.append([name, "N/A", "N/A", "N/A", "N/A", "N/A"])
        else:
            table_data.append([
                name,
                f"{s['accuracy']:.1f}" if s["accuracy"] is not None else "N/A",
                f"{s['avg_response_time_ms']:.1f}" if s["avg_response_time_ms"] is not None else "N/A",
                f"{s['avg_safety_score']:.1f}" if s["avg_safety_score"] is not None else "N/A",
                f"{s['avg_quality_score']:.1f}" if s["avg_quality_score"] is not None else "N/A",
                f"{s['overall_score']:.1f}" if s["overall_score"] is not None else "N/A",
            ])

    comparison_table = Table(table_data, colWidths=[4 * cm, 2.5 * cm, 2.7 * cm, 2 * cm, 2 * cm, 2 * cm])
    comparison_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A3B18A")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3A5A40")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(comparison_table)
    story.append(Spacer(1, 16))

    # ---- 8. User study results ----
    story.append(Paragraph("User Study Results", heading_style))
    participant_count = db.get_user_study_participant_count()
    if participant_count < 10:
        story.append(Paragraph(
            f"User study in progress: {participant_count} / 10 minimum participants "
            "completed. Ratings below reflect responses collected so far.",
            styles["Normal"],
        ))
    study_data = [["Chatbot", "Avg Accuracy", "Avg Clarity", "Avg Trust", "Avg Overall", "Responses"]]
    for name in CHATBOT_NAMES:
        info = user_study_averages_raw.get(name)
        if info:
            study_data.append([
                name, info["avg_accuracy"], info["avg_clarity"],
                info["avg_trust"], info["avg_overall"], info["response_count"],
            ])
        else:
            study_data.append([name, "N/A", "N/A", "N/A", "N/A", 0])
    study_table = Table(study_data, colWidths=[4 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 2 * cm])
    study_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A3B18A")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#588157")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(study_table)
    story.append(Spacer(1, 16))

    # ---- 9. Overall ranking ----
    story.append(Paragraph("Overall Ranking", heading_style))
    story.append(Paragraph(
        "Overall Score = Accuracy × {accuracy:.2f} + Safety × {safety:.2f} + "
        "User Rating × {user_rating:.2f} + Quality × {quality:.2f} + Speed × {speed:.2f} "
        "(all components normalized to 0-100; a component is proportionally excluded, "
        "not fabricated, if no data exists for it yet).".format(**OVERALL_SCORE_WEIGHTS),
        styles["Normal"],
    ))
    story.append(Spacer(1, 6))

    if ranking:
        rank_lines = [
            f"{i + 1}. {row['chatbot_name']} — {row['overall_score']:.1f} / 100"
            for i, row in enumerate(ranking)
        ]
        for line in rank_lines:
            story.append(Paragraph(line, styles["Normal"]))
    else:
        story.append(Paragraph("No ranking available (insufficient data).", styles["Normal"]))

    story.append(Spacer(1, 16))

    # ---- 10. Conclusion ----
    story.append(Paragraph("Conclusion", heading_style))
    if ranking:
        best = ranking[0]
        story.append(Paragraph(
            f"Based on run #{run['id']}, {best['chatbot_name']} achieved the highest "
            f"overall comparative score ({best['overall_score']:.1f}/100) across the "
            "weighted accuracy, safety, user-rating, quality, and speed criteria "
            "defined above. This reflects performance on this specific 50-question "
            "evaluation set and should be interpreted as an architecture-comparison "
            "result for this final-year project, not a clinical claim.",
            styles["Normal"],
        ))
    else:
        story.append(Paragraph(
            "No overall ranking could be computed for this run.", styles["Normal"]
        ))

    doc.build(story)
    return buffer.getvalue()

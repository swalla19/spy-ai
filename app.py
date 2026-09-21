"""AI Exam Paper Generator - Gradio Web Application.

A universal, subject-agnostic examination paper generator using Google Gemini AI,
Pydantic validation, dynamic pattern builders, and ReportLab PDF compilation.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import gradio as gr
from dotenv import load_dotenv

# Load environment
load_dotenv()

from models.exam_models import ExamPaper, ExamBlueprint
from services.exam_generator import ExamGeneratorService
from utils.pdf_generator import generate_exam_pdf, safe_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExamGeneratorApp")

# Initial question pattern preset
DEFAULT_PATTERN = [
    ["MCQ", 10, 1],
    ["Short Answer", 5, 2],
    ["Medium Answer", 4, 5],
    ["Long Answer", 2, 10],
]

DEFAULT_SUBJECT = "Compiler Construction"
DEFAULT_SYLLABUS = """Unit 1: Lexical Analysis & Regular Expressions
Unit 2: Syntax Analysis, Context-Free Grammars & Top-Down/Bottom-Up Parsing
Unit 3: Semantic Analysis, Type Checking & Symbol Tables
Unit 4: Intermediate Code Generation (Three-Address Code)
Unit 5: Code Optimization Techniques & Register Allocation
Unit 6: Target Code Generation"""

PRESETS = {
    "Compiler Construction (60 Marks)": {
        "subject": "Compiler Construction",
        "syllabus": DEFAULT_SYLLABUS,
        "total_marks": 60,
        "duration": "2 Hours",
        "pattern": [["MCQ", 10, 1], ["Short Answer", 5, 2], ["Medium Answer", 4, 5], ["Long Answer", 2, 10]],
        "easy": 30, "medium": 50, "hard": 20,
        "topics": "Lexical Analysis: 15%\nSyntax Analysis: 25%\nSemantic Analysis: 15%\nIntermediate Code: 15%\nCode Optimization: 15%\nCode Generation: 15%"
    },
    "Physics: Thermodynamics & Waves (50 Marks)": {
        "subject": "Physics: Thermodynamics & Optics",
        "syllabus": """Chapter 1: Zeroth & First Laws of Thermodynamics, Work and Heat
Chapter 2: Second Law, Heat Engines, Carnot Cycle, and Entropy
Chapter 3: Kinetic Theory of Gases & Mean Free Path
Chapter 4: Wave Motion, Superposition Principle & Interference of Light
Chapter 5: Diffraction & Polarization""",
        "total_marks": 50,
        "duration": "2 Hours",
        "pattern": [["MCQ", 5, 1], ["Short Answer", 5, 3], ["Numerical / Problem", 4, 5], ["Long Answer", 1, 10]],
        "easy": 25, "medium": 55, "hard": 20,
        "topics": "Thermodynamics: 40%\nKinetic Theory: 20%\nOptics & Wave Motion: 40%"
    },
    "World History: Modern Era (40 Marks)": {
        "subject": "World History: 1914 - 1990",
        "syllabus": """Theme 1: Causes and Consequences of World War I & The League of Nations
Theme 2: The Russian Revolution (1917) and the Rise of Soviet State
Theme 3: The Great Depression and Rise of Fascism in Europe
Theme 4: World War II and the Holocaust
Theme 5: Decolonization in Asia and Africa & The Cold War Dynamic""",
        "total_marks": 40,
        "duration": "1.5 Hours",
        "pattern": [["MCQ", 5, 1], ["Short Answer", 5, 3], ["Medium Answer", 2, 5], ["Long Essay", 1, 10]],
        "easy": 30, "medium": 45, "hard": 25,
        "topics": "World War I & League: 20%\nRussian Revolution: 20%\nRise of Fascism: 20%\nDecolonization & Cold War: 40%"
    },
    "Macroeconomics: Principles (30 Marks)": {
        "subject": "Principles of Macroeconomics",
        "syllabus": """Module 1: National Income Accounting (GDP, GNP, Nominal vs Real)
Module 2: Classical vs Keynesian Determination of Output & Employment
Module 3: Money Supply, Central Banking, and Monetary Policy Tools
Module 4: Inflation, Unemployment & The Phillips Curve""",
        "total_marks": 30,
        "duration": "1 Hour",
        "pattern": [["MCQ", 5, 1], ["Short Answer", 5, 2], ["Analytical Problem", 3, 5]],
        "easy": 30, "medium": 50, "hard": 20,
        "topics": "National Income: 30%\nKeynesian Model: 30%\nMonetary Policy & Inflation: 40%"
    }
}


def render_exam_html(exam_paper: Optional[ExamPaper], show_answers: bool = True) -> str:
    """Renders the examination paper in an authentic academic format."""
    if not exam_paper:
        return """
        <div style="text-align: center; padding: 60px 20px; color: #64748b; background: #f8fafc; border-radius: 12px; border: 2px dashed #cbd5e1;">
            <div style="font-size: 42px; margin-bottom: 12px;">📄</div>
            <h3 style="font-size: 18px; color: #334155; margin-bottom: 6px;">No Examination Paper Generated Yet</h3>
            <p style="font-size: 14px; max-width: 440px; margin: 0 auto;">Configure your exam parameters on the left, generate an exam blueprint, and click <b>Generate Exam Paper</b>.</p>
        </div>
        """

    exam = exam_paper.exam

    # Instructions list
    instructions_html = "".join(f"<li>{safe_text(inst)}</li>" for inst in exam.instructions)

    # Sections & Questions
    sections_html = ""
    for sec in exam_paper.sections:
        sec_inst = f"<p style='text-align: center; font-style: italic; color: #475569; font-size: 13px; margin-bottom: 16px;'>{safe_text(sec.instructions)}</p>" if sec.instructions else ""
        
        q_cards = ""
        for q in sec.questions:
            # Format MCQ options
            options_html = ""
            if q.options and len(q.options) >= 2:
                opt_items = "".join(f"<div style='background: #f8fafc; border: 1px solid #e2e8f0; padding: 6px 12px; border-radius: 6px; font-size: 13.5px; color: #1e293b;'>{safe_text(opt)}</div>" for opt in q.options)
                options_html = f"<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0 10px 24px;'>{opt_items}</div>"

            # Format Internal choice if any
            internal_choice_html = ""
            if q.internal_choice:
                internal_choice_html = f"""
                <div style='margin-left: 24px; margin-top: 8px; padding-left: 12px; border-left: 3px solid #94a3b8;'>
                    <div style='font-size: 11px; font-weight: bold; color: #64748b; text-transform: uppercase;'>--- OR ---</div>
                    <div style='font-size: 14px; color: #1e293b; margin-top: 4px;'>{safe_text(q.internal_choice)}</div>
                </div>
                """

            # Answer key badge
            ans_html = ""
            if show_answers and q.answer:
                ans_html = f"""
                <div style='margin-top: 8px; margin-left: 24px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; padding: 8px 12px; font-size: 12.5px; color: #065f46;'>
                    <b>Answer Key / Rubric:</b> {safe_text(q.answer)}
                </div>
                """

            bloom_badge = f"<span style='background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 8px;'>{safe_text(q.bloom_level)}</span>" if q.bloom_level else ""
            diff_badge = f"<span style='background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; margin-left: 6px;'>{safe_text(q.difficulty)}</span>"
            topic_badge = f"<span style='background: #f3e8ff; color: #7e22ce; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; margin-left: 6px;'>{safe_text(q.topic)}</span>"

            q_cards += f"""
            <div style='padding: 12px 14px; margin-bottom: 12px; background: #ffffff; border: 1px solid #f1f5f9; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);'>
                <div style='display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;'>
                    <div style='font-size: 14.5px; color: #0f172a; line-height: 1.5;'>
                        <b style='color: #1e293b;'>Q{q.number}.</b> {safe_text(q.question)}
                    </div>
                    <div style='white-space: nowrap; font-size: 13.5px; font-weight: bold; color: #0f172a; background: #f8fafc; border: 1px solid #e2e8f0; padding: 3px 8px; border-radius: 6px;'>
                        [{q.marks}M]
                    </div>
                </div>
                {options_html}
                {internal_choice_html}
                <div style='margin-top: 8px; display: flex; align-items: center; flex-wrap: wrap;'>
                    <span style='font-size: 11px; color: #94a3b8;'>Metadata:</span>
                    {bloom_badge}
                    {diff_badge}
                    {topic_badge}
                </div>
                {ans_html}
            </div>
            """

        sections_html += f"""
        <div style='margin-top: 24px; margin-bottom: 16px;'>
            <div style='text-align: center; border-bottom: 2px solid #0f172a; padding-bottom: 6px; margin-bottom: 12px;'>
                <h3 style='font-size: 15px; font-weight: bold; color: #0f172a; letter-spacing: 0.5px; margin: 0; text-transform: uppercase;'>
                    {safe_text(sec.name)}
                </h3>
            </div>
            {sec_inst}
            {q_cards}
        </div>
        """

    html = f"""
    <div style='max-width: 860px; margin: 0 auto; background: #ffffff; padding: 36px 40px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;'>
        <!-- Header -->
        <div style='text-align: center; margin-bottom: 16px;'>
            <h1 style='font-size: 20px; font-weight: 800; letter-spacing: 1.5px; color: #0f172a; margin: 0 0 6px 0; text-transform: uppercase;'>
                {safe_text(exam.title)}
            </h1>
            <h2 style='font-size: 17px; font-weight: 700; color: #334155; margin: 0 0 16px 0; text-transform: uppercase; letter-spacing: 0.5px;'>
                {safe_text(exam.subject)}
            </h2>
        </div>

        <!-- Banner Table -->
        <div style='display: flex; justify-content: space-between; border-top: 2px solid #0f172a; border-bottom: 2px solid #0f172a; padding: 8px 12px; margin-bottom: 16px; font-size: 13.5px; font-weight: 600; color: #1e293b;'>
            <div>TIME ALLOWED: <span style='font-weight: normal;'>{safe_text(exam.duration)}</span></div>
            <div>MAXIMUM MARKS: <span style='font-weight: normal;'>{exam.total_marks}</span></div>
        </div>

        <!-- Instructions -->
        <div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px;'>
            <div style='font-size: 12px; font-weight: bold; color: #334155; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;'>General Instructions:</div>
            <ul style='margin: 0; padding-left: 20px; font-size: 13px; color: #475569; line-height: 1.5;'>
                {instructions_html}
            </ul>
        </div>

        <!-- Paper Body -->
        {sections_html}
        
        <div style='text-align: center; margin-top: 30px; padding-top: 16px; border-top: 1px dashed #cbd5e1; font-size: 12px; color: #94a3b8;'>
            *** END OF EXAMINATION PAPER ***
        </div>
    </div>
    """
    return html


def format_blueprint_markdown(bp: Optional[ExamBlueprint], error_msg: Optional[str] = None) -> str:
    """Formats the blueprint display card with validation badges."""
    if error_msg:
        return f"""
<div style="background: #fef2f2; border: 1px solid #fecaca; padding: 16px; border-radius: 10px; color: #991b1b;">
    <div style="display: flex; align-items: center; gap: 8px; font-weight: bold; font-size: 15px; margin-bottom: 6px;">
        <span>⚠️ Validation Error</span>
    </div>
    <div style="white-space: pre-wrap; font-size: 13.5px; line-height: 1.5;">{safe_text(error_msg)}</div>
</div>
"""

    if not bp:
        return """
<div style="padding: 20px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px; color: #64748b; text-align: center;">
    Click <b>Generate Blueprint</b> to review question tally, marks distribution, and syllabus coverage before paper synthesis.
</div>
"""

    pattern_rows = "".join(
        f"<tr><td style='padding: 6px 12px; border-bottom: 1px solid #f1f5f9;'>{p.question_type}</td>"
        f"<td style='padding: 6px 12px; border-bottom: 1px solid #f1f5f9; text-align: center;'>{p.count}</td>"
        f"<td style='padding: 6px 12px; border-bottom: 1px solid #f1f5f9; text-align: center;'>{p.marks_per_question}M</td>"
        f"<td style='padding: 6px 12px; border-bottom: 1px solid #f1f5f9; text-align: right; font-weight: 600;'>{p.total_marks}M</td></tr>"
        for p in bp.pattern
    )

    topic_summary = "Intelligently balanced across full syllabus"
    if bp.topic_weights:
        topic_summary = ", ".join(f"{t}: {w}%" for t, w in bp.topic_weights.items())

    return f"""
<div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 18px; border-radius: 10px; color: #166534; font-family: inherit;">
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #bbf7d0; padding-bottom: 10px; margin-bottom: 12px;">
        <span style="font-size: 16px; font-weight: 800; text-transform: uppercase;">📋 Exam Blueprint Validated</span>
        <span style="background: #15803d; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700;">
            Total: {bp.total_marks} Marks ({bp.duration})
        </span>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; margin-bottom: 14px; color: #1e293b;">
        <div><b>Subject:</b> {safe_text(bp.subject)}</div>
        <div><b>Total Questions:</b> {bp.total_questions} Questions</div>
        <div><b>Difficulty Distribution:</b> Easy {bp.difficulty.easy}% | Med {bp.difficulty.medium}% | Hard {bp.difficulty.hard}%</div>
        <div><b>Topic Strategy:</b> {safe_text(topic_summary)}</div>
    </div>

    <table style="width: 100%; border-collapse: collapse; font-size: 12.5px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.05); color: #1e293b;">
        <thead style="background: #f8fafc; font-weight: 700; color: #475569; text-transform: uppercase; font-size: 11px;">
            <tr>
                <th style="padding: 8px 12px; text-align: left;">Type</th>
                <th style="padding: 8px 12px; text-align: center;">Count</th>
                <th style="padding: 8px 12px; text-align: center;">Marks / Q</th>
                <th style="padding: 8px 12px; text-align: right;">Subtotal</th>
            </tr>
        </thead>
        <tbody>
            {pattern_rows}
            <tr style="background: #f8fafc; font-weight: bold;">
                <td colspan="3" style="padding: 8px 12px; text-align: right;">Total Generated Marks:</td>
                <td style="padding: 8px 12px; text-align: right; color: #15803d; font-size: 13px;">{bp.calculated_marks} Marks</td>
            </tr>
        </tbody>
    </table>
</div>
"""


# ==========================================
# Gradio Interface Callbacks
# ==========================================

def handle_apply_preset(preset_key: str):
    """Loads pre-configured subject presets."""
    preset = PRESETS.get(preset_key)
    if not preset:
        return (gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
    return (
        preset["subject"],
        preset["syllabus"],
        preset["total_marks"],
        preset["duration"],
        preset["easy"],
        preset["medium"],
        preset["hard"],
        preset["pattern"],
        preset["topics"]
    )


def handle_add_pattern_row(current_pattern: List[List[Any]]):
    """Adds a new question type row to the pattern table."""
    pattern = current_pattern if current_pattern else []
    new_pattern = list(pattern)
    new_pattern.append(["New Question Type", 2, 5])
    return new_pattern


def handle_set_mixed_difficulty():
    """Sets standard balanced difficulty (30% Easy, 50% Medium, 20% Hard)."""
    return 30, 50, 20


def extract_pattern_rows(pattern_data: Any) -> List[Dict[str, Any]]:
    """Robust extractor for Gradio Dataframe data (handles DataFrame, dict, or list of lists)."""
    if pattern_data is None:
        return []

    raw_rows = []
    if isinstance(pattern_data, dict):
        raw_rows = pattern_data.get("data", [])
    elif hasattr(pattern_data, "values"):
        raw_rows = pattern_data.values.tolist() if hasattr(pattern_data.values, "tolist") else list(pattern_data.values)
    elif isinstance(pattern_data, list):
        raw_rows = pattern_data

    extracted = []
    for row in raw_rows:
        if isinstance(row, (list, tuple)) and len(row) >= 3:
            q_type = str(row[0] if row[0] is not None else "").strip()
            if not q_type:
                continue
            try:
                count = int(float(row[1]))
                marks = int(float(row[2]))
                if count > 0 and marks > 0:
                    extracted.append({
                        "question_type": q_type,
                        "count": count,
                        "marks_per_question": marks
                    })
            except (ValueError, TypeError):
                continue
        elif isinstance(row, dict):
            q_type = str(row.get("Question Type") or row.get("question_type") or "").strip()
            if not q_type:
                continue
            try:
                count = int(float(row.get("Number of Questions") or row.get("count") or 0))
                marks = int(float(row.get("Marks Per Question") or row.get("marks_per_question") or 0))
                if count > 0 and marks > 0:
                    extracted.append({
                        "question_type": q_type,
                        "count": count,
                        "marks_per_question": marks
                    })
            except (ValueError, TypeError):
                continue

    return extracted


def handle_generate_blueprint(
    subject: str,
    syllabus: str,
    total_marks: float,
    duration: str,
    easy_pct: int,
    medium_pct: int,
    hard_pct: int,
    pattern_data: Any,
    topic_weights: str,
    inc_ans: bool,
    inc_choice: bool,
    follow_blooms: bool,
    avoid_dups: bool
) -> Tuple[str, Optional[Dict[str, Any]], str]:
    """Generates and validates the exam blueprint."""
    pattern_rows = extract_pattern_rows(pattern_data)

    blueprint, error_msg = ExamGeneratorService.create_blueprint(
        subject=subject,
        syllabus=syllabus,
        total_marks=int(float(total_marks or 0)),
        duration=duration,
        easy_pct=easy_pct,
        medium_pct=medium_pct,
        hard_pct=hard_pct,
        pattern_items=pattern_rows,
        topic_weights_text=topic_weights,
        include_answer_key=inc_ans,
        include_internal_choices=inc_choice,
        follow_blooms_taxonomy=follow_blooms,
        avoid_duplicates=avoid_dups
    )

    if error_msg:
        html = format_blueprint_markdown(None, error_msg)
        return html, None, f"⚠️ Validation Error: {error_msg.splitlines()[0]}"

    html = format_blueprint_markdown(blueprint)
    return html, blueprint.model_dump(), "✅ Blueprint generated and validated successfully."


def handle_generate_paper(
    blueprint_state: Optional[Dict[str, Any]],
    subject: str,
    syllabus: str,
    total_marks: float,
    duration: str,
    easy_pct: int,
    medium_pct: int,
    hard_pct: int,
    pattern_data: Any,
    topic_weights: str,
    inc_ans: bool,
    inc_choice: bool,
    follow_blooms: bool,
    avoid_dups: bool,
    progress=gr.Progress(track_tqdm=True)
) -> Tuple[str, Optional[Dict[str, Any]], Dict[str, Any], gr.update, str, Optional[str]]:
    """Generates the full examination paper via Gemini, validates, and renders."""
    progress(0.1, desc="Checking blueprint & parameters...")

    pattern_rows = extract_pattern_rows(pattern_data)

    blueprint, error_msg = ExamGeneratorService.create_blueprint(
        subject=subject,
        syllabus=syllabus,
        total_marks=int(float(total_marks or 0)),
        duration=duration,
        easy_pct=easy_pct,
        medium_pct=medium_pct,
        hard_pct=hard_pct,
        pattern_items=pattern_rows,
        topic_weights_text=topic_weights,
        include_answer_key=inc_ans,
        include_internal_choices=inc_choice,
        follow_blooms_taxonomy=follow_blooms,
        avoid_duplicates=avoid_dups
    )

    if error_msg:
        gr.Warning(error_msg)
        return render_exam_html(None), None, {}, gr.update(choices=[], value=None), f"❌ Error: {error_msg.splitlines()[0]}", None

    progress(0.3, desc=f"Prompting Gemini ({blueprint.subject})...")

    try:
        exam_paper = ExamGeneratorService.generate_exam_paper(blueprint)
    except Exception as e:
        logger.exception("Paper generation failed: %s", str(e))
        err_text = str(e)
        gr.Error(err_text)
        return render_exam_html(None), None, {}, gr.update(choices=[], value=None), f"❌ Generation Failed: {err_text}", None

    progress(0.85, desc="Formatting paper layout...")

    paper_dict = exam_paper.model_dump()
    paper_html = render_exam_html(exam_paper, show_answers=inc_ans)

    # Populate question dropdown choices for single-question regeneration
    all_qs = exam_paper.get_all_questions()
    q_choices = [f"Q{q.number}: {q.type} ({q.marks}M) - {q.topic[:25]}..." for q in all_qs]
    default_choice = q_choices[0] if q_choices else None

    # Pre-generate PDF so it's ready for instant download
    progress(0.95, desc="Compiling PDF document...")
    try:
        pdf_path = generate_exam_pdf(exam_paper)
    except Exception as e:
        logger.error("Initial PDF compilation notice: %s", str(e))
        pdf_path = None

    progress(1.0, desc="Done!")
    return (
        paper_html,
        paper_dict,
        paper_dict,
        gr.update(choices=q_choices, value=default_choice),
        f"✅ Successfully generated {len(all_qs)} questions ({exam_paper.total_calculated_marks()} marks) for '{exam_paper.exam.subject}'!",
        pdf_path
    )


def handle_regenerate_question(
    paper_state: Optional[Dict[str, Any]],
    selected_choice: Optional[str],
    inc_ans: bool,
    progress=gr.Progress(track_tqdm=True)
) -> Tuple[str, Optional[Dict[str, Any]], Dict[str, Any], str, Optional[str]]:
    """Regenerates a single question within the active paper."""
    if not paper_state:
        gr.Warning("No active exam paper to regenerate from.")
        return render_exam_html(None), None, {}, "⚠️ No active exam paper.", None

    if not selected_choice:
        gr.Warning("Please select a question from the dropdown to regenerate.")
        return render_exam_html(ExamPaper.model_validate(paper_state)), paper_state, paper_state, "⚠️ Select a question first.", None

    # Parse question number e.g. "Q3: Short Answer (2M)..." -> 3
    try:
        q_num = int(selected_choice.split(":")[0].replace("Q", "").strip())
    except Exception:
        gr.Warning("Could not determine question number from selection.")
        return render_exam_html(ExamPaper.model_validate(paper_state)), paper_state, paper_state, "⚠️ Invalid question format.", None

    progress(0.3, desc=f"Regenerating Question #{q_num} with Gemini...")

    try:
        current_paper = ExamPaper.model_validate(paper_state)
        updated_paper, msg = ExamGeneratorService.regenerate_question(current_paper, q_num)
    except Exception as e:
        logger.exception("Single question regeneration failed: %s", str(e))
        gr.Error(str(e))
        return render_exam_html(ExamPaper.model_validate(paper_state)), paper_state, paper_state, f"❌ Failed: {str(e)}", None

    progress(0.8, desc="Re-rendering exam paper...")
    updated_dict = updated_paper.model_dump()
    paper_html = render_exam_html(updated_paper, show_answers=inc_ans)

    # Recompile PDF
    try:
        pdf_path = generate_exam_pdf(updated_paper)
    except Exception:
        pdf_path = None

    progress(1.0, desc="Regenerated!")
    return paper_html, updated_dict, updated_dict, f"✅ {msg}", pdf_path


def handle_download_pdf(paper_state: Optional[Dict[str, Any]]) -> Optional[str]:
    """Generates the PDF file for download."""
    if not paper_state:
        gr.Warning("Generate an exam paper first before downloading PDF.")
        return None

    try:
        paper = ExamPaper.model_validate(paper_state)
        pdf_path = generate_exam_pdf(paper)
        return pdf_path
    except Exception as e:
        logger.exception("PDF generation error: %s", str(e))
        gr.Error(f"Failed to generate PDF: {str(e)}")
        return None


def handle_clear_all():
    """Resets all fields to blank / initial default state."""
    return (
        "",
        "",
        50,
        "2 Hours",
        30,
        50,
        20,
        DEFAULT_PATTERN,
        "",
        format_blueprint_markdown(None),
        None,
        render_exam_html(None),
        None,
        {},
        gr.update(choices=[], value=None),
        "Ready to generate new exam paper.",
        None
    )


# ==========================================
# Gradio UI Construction
# ==========================================

custom_css = """
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}
.app-header {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: white;
    padding: 24px 30px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.app-title {
    font-size: 26px !important;
    font-weight: 800 !important;
    margin: 0 0 6px 0 !important;
    letter-spacing: -0.5px;
}
.app-subtitle {
    font-size: 14px !important;
    color: #94a3b8 !important;
    margin: 0 !important;
}
.card-panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 14px;
}
.primary-btn {
    background: #2563eb !important;
    color: white !important;
    font-weight: 600 !important;
}
.blueprint-btn {
    background: #0f766e !important;
    color: white !important;
    font-weight: 600 !important;
}
"""

with gr.Blocks(title="AI Exam Paper Generator") as demo:
    # State stores
    current_blueprint_state = gr.State(None)
    current_paper_state = gr.State(None)

    # Header
    gr.HTML("""
    <div class="app-header">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <h1 class="app-title">🎓 AI Exam Paper Generator</h1>
                <p class="app-subtitle">Generate structured, academically rigorous examination papers for any subject using Gemini AI</p>
            </div>
            <div style="background: rgba(255, 255, 255, 0.1); padding: 6px 14px; border-radius: 8px; font-size: 12.5px; border: 1px solid rgba(255, 255, 255, 0.15);">
                ✨ Powered by <b>Google Gemini 3.6 Flash</b> &amp; ReportLab
            </div>
        </div>
    </div>
    """)

    # Status Notification Banner
    status_box = gr.Markdown(value="👋 Welcome! Select a preset or configure your exam below.", elem_id="status-banner")

    # Subject Presets row
    with gr.Row():
        preset_dropdown = gr.Dropdown(
            label="⚡ Quick Load Subject Presets (Optional)",
            choices=list(PRESETS.keys()),
            value="Compiler Construction (60 Marks)",
            scale=4
        )
        load_preset_btn = gr.Button("Load Preset", variant="secondary", scale=1)

    # Main 2-Column Layout
    with gr.Row():
        # ==========================================
        # LEFT COLUMN: Configuration
        # ==========================================
        with gr.Column(scale=5):
            gr.Markdown("### ⚙️ 1. Exam Configuration")

            subject_input = gr.Textbox(
                label="Subject Name",
                placeholder="e.g. Physics, Compiler Construction, World History, Economics...",
                value=DEFAULT_SUBJECT
            )

            syllabus_input = gr.Textbox(
                label="Syllabus / Topics",
                placeholder="Enter units, chapters, modules, or key concepts...",
                value=DEFAULT_SYLLABUS,
                lines=6
            )

            with gr.Row():
                total_marks_input = gr.Number(
                    label="Total Marks",
                    value=60,
                    precision=0,
                    minimum=1,
                    scale=1
                )
                duration_input = gr.Dropdown(
                    label="Exam Duration",
                    choices=["45 Minutes", "1 Hour", "1.5 Hours", "2 Hours", "2.5 Hours", "3 Hours"],
                    value="2 Hours",
                    allow_custom_value=True,
                    scale=1
                )

            # Difficulty Distribution
            with gr.Group():
                gr.Markdown("**Difficulty Distribution (%)**")
                with gr.Row():
                    easy_slider = gr.Slider(0, 100, value=30, step=5, label="Easy %")
                    med_slider = gr.Slider(0, 100, value=50, step=5, label="Medium %")
                    hard_slider = gr.Slider(0, 100, value=20, step=5, label="Hard %")
                mixed_btn = gr.Button("Set Mixed / Balanced (30 / 50 / 20)", size="sm")

            # Dynamic Question Pattern Builder
            with gr.Group():
                gr.Markdown("**Dynamic Question Pattern Builder**")
                gr.Markdown(
                    "<span style='font-size: 12px; color: #64748b;'>Configure question types, counts, and mark allocations. Pattern marks must match Total Marks.</span>"
                )
                pattern_table = gr.Dataframe(
                    headers=["Question Type", "Number of Questions", "Marks Per Question"],
                    datatype=["str", "number", "number"],
                    value=DEFAULT_PATTERN,
                    column_count=(3, "fixed"),
                    row_count=(4, "dynamic"),
                    interactive=True,
                    wrap=True
                )
                add_row_btn = gr.Button("+ Add Question Type Row", size="sm")

            # Topic Weightage (Optional)
            with gr.Accordion("Optional: Custom Topic Weightages", open=False):
                topic_weights_input = gr.Textbox(
                    label="Topic Distribution (Optional)",
                    placeholder="e.g.:\nThermodynamics: 30%\nHeat Transfer: 30%\nFluid Mechanics: 40%",
                    lines=3
                )

            # Additional Options
            with gr.Group():
                gr.Markdown("**Pedagogical & Structural Options**")
                with gr.Row():
                    inc_ans_check = gr.Checkbox(label="Include Answer Key", value=True)
                    inc_choice_check = gr.Checkbox(label="Include Internal Choices ('OR')", value=False)
                with gr.Row():
                    blooms_check = gr.Checkbox(label="Follow Bloom's Taxonomy", value=True)
                    dups_check = gr.Checkbox(label="Avoid Duplicate Questions", value=True)

            with gr.Row():
                clear_btn = gr.Button("Clear All", variant="secondary")
                gen_blueprint_btn = gr.Button("Generate Blueprint", variant="primary", elem_classes=["blueprint-btn"])

            # Exam Blueprint Section
            gr.Markdown("### 📐 2. Exam Blueprint")
            blueprint_preview = gr.HTML(value=format_blueprint_markdown(None))

            gen_paper_btn = gr.Button("🚀 Generate Exam Paper", variant="primary", size="lg", elem_classes=["primary-btn"])

        # ==========================================
        # RIGHT COLUMN: Generated Paper & Management
        # ==========================================
        with gr.Column(scale=7):
            gr.Markdown("### 📄 Generated Examination Paper")

            # Action bar above paper
            with gr.Row():
                download_pdf_btn = gr.Button("📥 Download PDF", variant="secondary")
                pdf_file_output = gr.File(label="Generated PDF File", visible=True)

            # Main paper viewer
            paper_view = gr.HTML(value=render_exam_html(None))

            # Question Manager & Single Regenerator
            with gr.Group():
                gr.Markdown("### 🔄 Regenerate Specific Question")
                gr.Markdown(
                    "<span style='font-size: 12px; color: #64748b;'>Select any question to regenerate it individually with the same topic, difficulty, and marks without recreating the whole paper.</span>"
                )
                with gr.Row():
                    question_selector = gr.Dropdown(
                        label="Select Question to Regenerate",
                        choices=[],
                        value=None,
                        scale=4
                    )
                    regen_q_btn = gr.Button("Regenerate Selected", variant="secondary", scale=2)

            # View JSON Debugger Accordion
            with gr.Accordion("🔍 View Structured JSON (for Debugging & Integration)", open=False):
                json_debug_view = gr.JSON(label="Raw Pydantic JSON")

    # ==========================================
    # Event Wire-ups
    # ==========================================

    # Load Preset
    load_preset_btn.click(
        fn=handle_apply_preset,
        inputs=[preset_dropdown],
        outputs=[
            subject_input,
            syllabus_input,
            total_marks_input,
            duration_input,
            easy_slider,
            med_slider,
            hard_slider,
            pattern_table,
            topic_weights_input
        ]
    )

    # Preset dropdown change also triggers load
    preset_dropdown.change(
        fn=handle_apply_preset,
        inputs=[preset_dropdown],
        outputs=[
            subject_input,
            syllabus_input,
            total_marks_input,
            duration_input,
            easy_slider,
            med_slider,
            hard_slider,
            pattern_table,
            topic_weights_input
        ]
    )

    # Mixed difficulty preset button
    mixed_btn.click(
        fn=handle_set_mixed_difficulty,
        outputs=[easy_slider, med_slider, hard_slider]
    )

    # Add row to question pattern
    add_row_btn.click(
        fn=handle_add_pattern_row,
        inputs=[pattern_table],
        outputs=[pattern_table]
    )

    # Generate Blueprint
    gen_blueprint_btn.click(
        fn=handle_generate_blueprint,
        inputs=[
            subject_input,
            syllabus_input,
            total_marks_input,
            duration_input,
            easy_slider,
            med_slider,
            hard_slider,
            pattern_table,
            topic_weights_input,
            inc_ans_check,
            inc_choice_check,
            blooms_check,
            dups_check
        ],
        outputs=[blueprint_preview, current_blueprint_state, status_box]
    )

    # Generate Full Exam Paper
    gen_paper_btn.click(
        fn=handle_generate_paper,
        inputs=[
            current_blueprint_state,
            subject_input,
            syllabus_input,
            total_marks_input,
            duration_input,
            easy_slider,
            med_slider,
            hard_slider,
            pattern_table,
            topic_weights_input,
            inc_ans_check,
            inc_choice_check,
            blooms_check,
            dups_check
        ],
        outputs=[
            paper_view,
            current_paper_state,
            json_debug_view,
            question_selector,
            status_box,
            pdf_file_output
        ]
    )

    # Regenerate Single Question
    regen_q_btn.click(
        fn=handle_regenerate_question,
        inputs=[current_paper_state, question_selector, inc_ans_check],
        outputs=[
            paper_view,
            current_paper_state,
            json_debug_view,
            status_box,
            pdf_file_output
        ]
    )

    # Download PDF
    download_pdf_btn.click(
        fn=handle_download_pdf,
        inputs=[current_paper_state],
        outputs=[pdf_file_output]
    )

    # Clear All
    clear_btn.click(
        fn=handle_clear_all,
        outputs=[
            subject_input,
            syllabus_input,
            total_marks_input,
            duration_input,
            easy_slider,
            med_slider,
            hard_slider,
            pattern_table,
            topic_weights_input,
            blueprint_preview,
            current_blueprint_state,
            paper_view,
            current_paper_state,
            json_debug_view,
            question_selector,
            status_box,
            pdf_file_output
        ]
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        theme=gr.themes.Soft(primary_hue="blue"),
        css=custom_css
    )

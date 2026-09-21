"""Exam Generator Orchestrator.

Manages blueprint validation, coordination between prompts, Gemini AI service,
response validation, and single-question regeneration.
"""

from typing import Dict, Any, List, Optional, Tuple
import re

from models.exam_models import (
    ExamPaper,
    ExamBlueprint,
    QuestionPatternItem,
    DifficultyDistribution,
    Question,
    SingleQuestionRegenRequest
)
from utils.prompts import (
    build_exam_generation_prompt,
    build_question_regeneration_prompt,
    SYSTEM_PROMPT
)
from services.gemini_service import gemini_service
from services.validator import ExamValidator


class ExamGeneratorService:
    """Core coordinator for exam paper generation and manipulation."""

    @classmethod
    def create_blueprint(
        cls,
        subject: str,
        syllabus: str,
        total_marks: int,
        duration: str,
        easy_pct: int,
        medium_pct: int,
        hard_pct: int,
        pattern_items: List[Dict[str, Any]],
        topic_weights_text: Optional[str] = None,
        include_answer_key: bool = True,
        include_internal_choices: bool = False,
        follow_blooms: bool = True,
        follow_blooms_taxonomy: Optional[bool] = None,
        avoid_duplicates: bool = True
    ) -> Tuple[Optional[ExamBlueprint], Optional[str]]:
        """Validates user configuration and calculates an ExamBlueprint.

        Returns (blueprint, None) on success or (None, error_message) on failure.
        """
        # Validate required fields
        if not subject or not subject.strip():
            return None, "Subject cannot be empty."

        if not syllabus or not syllabus.strip():
            return None, "Syllabus / Topics cannot be empty. Please enter topics or chapter outlines."

        if total_marks <= 0:
            return None, "Total Marks must be a positive number greater than 0."

        if not duration or not duration.strip():
            return None, "Exam Duration is required (e.g. '2 Hours')."

        if not pattern_items:
            return None, "Please configure at least one question type in the Question Pattern."

        # Parse question pattern rows
        parsed_pattern: List[QuestionPatternItem] = []
        calculated_marks = 0
        total_questions = 0

        for idx, row in enumerate(pattern_items, 1):
            q_type = str(row.get("question_type", "")).strip()
            if not q_type:
                return None, f"Question type name missing in row #{idx}."

            try:
                count = int(row.get("count", 0))
                marks_per_q = int(row.get("marks_per_question", 0))
            except (ValueError, TypeError):
                return None, f"Invalid count or marks in row #{idx} ('{q_type}'). Must be positive integers."

            if count <= 0 or marks_per_q <= 0:
                return None, f"Count and Marks per Question must be greater than 0 in row #{idx} ('{q_type}')."

            item = QuestionPatternItem(
                question_type=q_type,
                count=count,
                marks_per_question=marks_per_q
            )
            parsed_pattern.append(item)
            calculated_marks += item.total_marks
            total_questions += item.count

        # Strictly check marks match
        if calculated_marks != total_marks:
            diff = calculated_marks - total_marks
            sign = "more" if diff > 0 else "fewer"
            return None, (
                f"Marks Mismatch Error:\n"
                f"• Target Total Marks: {total_marks}\n"
                f"• Pattern Generated Marks: {calculated_marks} ({abs(diff)} marks {sign} than required).\n"
                f"Please adjust question counts or marks per question in the pattern builder so they match exactly."
            )

        # Parse difficulty distribution
        diff_dist = DifficultyDistribution(
            easy=int(easy_pct),
            medium=int(medium_pct),
            hard=int(hard_pct)
        )

        # Parse optional topic weights
        topic_weights: Optional[Dict[str, int]] = None
        if topic_weights_text and topic_weights_text.strip():
            topic_weights = {}
            for line in topic_weights_text.strip().splitlines():
                if ":" in line:
                    parts = line.split(":", 1)
                    t_name = parts[0].strip()
                    # extract numbers
                    num_match = re.search(r"\d+", parts[1])
                    if t_name and num_match:
                        topic_weights[t_name] = int(num_match.group())

        blueprint = ExamBlueprint(
            subject=subject.strip(),
            syllabus=syllabus.strip(),
            total_marks=total_marks,
            duration=duration.strip(),
            difficulty=diff_dist,
            pattern=parsed_pattern,
            total_questions=total_questions,
            calculated_marks=calculated_marks,
            topic_weights=topic_weights,
            include_answer_key=include_answer_key,
            include_internal_choices=include_internal_choices,
            follow_blooms_taxonomy=(follow_blooms_taxonomy if follow_blooms_taxonomy is not None else follow_blooms),
            avoid_duplicates=avoid_duplicates
        )
        return blueprint, None

    @classmethod
    def generate_exam_paper(cls, blueprint: ExamBlueprint) -> ExamPaper:
        """Sends the blueprint prompt to Gemini, validates the output, and returns the ExamPaper."""
        prompt = build_exam_generation_prompt(blueprint)

        # Call Gemini Service
        raw_json = gemini_service.generate_json(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3
        )

        # Validate and heal if necessary
        exam_paper = ExamValidator.validate_and_heal(
            raw_data=raw_json,
            blueprint=blueprint,
            gemini_service=gemini_service,
            max_attempts=2
        )

        return exam_paper

    @classmethod
    def regenerate_question(
        cls,
        exam_paper: ExamPaper,
        question_number: int
    ) -> Tuple[ExamPaper, str]:
        """Regenerates a single specific question in place within the exam paper.

        Returns (updated_exam_paper, success_message).
        """
        target_q: Optional[Question] = None
        target_section = None
        q_idx_in_section = -1

        # Locate target question
        for section in exam_paper.sections:
            for idx, q in enumerate(section.questions):
                if q.number == question_number:
                    target_q = q
                    target_section = section
                    q_idx_in_section = idx
                    break
            if target_q:
                break

        if not target_q or target_section is None:
            raise ValueError(f"Question #{question_number} was not found in the current examination paper.")

        req = SingleQuestionRegenRequest(
            subject=exam_paper.exam.subject,
            topic=target_q.topic,
            question_type=target_q.type,
            marks=target_q.marks,
            difficulty=target_q.difficulty,
            bloom_level=target_q.bloom_level,
            existing_question=target_q.question,
            include_answer_key=bool(target_q.answer)
        )

        prompt = build_question_regeneration_prompt(req)
        raw_json = gemini_service.generate_json(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7
        )

        # Format new question
        new_q = Question(
            number=question_number,
            type=raw_json.get("type", target_q.type),
            question=raw_json.get("question", "").strip(),
            options=raw_json.get("options"),
            answer=raw_json.get("answer"),
            marks=target_q.marks,
            topic=raw_json.get("topic", target_q.topic),
            difficulty=raw_json.get("difficulty", target_q.difficulty),
            bloom_level=raw_json.get("bloom_level", target_q.bloom_level),
            internal_choice=raw_json.get("internal_choice")
        )

        # Replace in section
        target_section.questions[q_idx_in_section] = new_q

        return exam_paper, f"Question #{question_number} successfully regenerated!"

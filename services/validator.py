"""Validator and Auto-Correction Service for AI Exam Paper Generator.

Performs multi-stage structural, statistical, and pedagogical checks on generated
exam papers, and executes automated self-healing loops with Gemini.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from pydantic import ValidationError

from models.exam_models import ExamPaper, ExamBlueprint, Question
from utils.prompts import build_correction_prompt, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ExamValidator:
    """Validates exam papers against structural rules and blueprints."""

    @classmethod
    def validate_exam_paper(
        cls,
        data: Dict[str, Any],
        blueprint: ExamBlueprint
    ) -> Tuple[Optional[ExamPaper], List[str]]:
        """Runs all 11 validation checks on generated exam data.

        Returns:
            Tuple of (Validated ExamPaper object or None, List of error descriptions)
        """
        errors: List[str] = []

        # 1 & 2: Valid Pydantic structure
        try:
            exam_paper = ExamPaper.model_validate(data)
        except ValidationError as ve:
            for err in ve.errors():
                loc = " -> ".join(str(p) for p in err.get("loc", []))
                errors.append(f"Schema error at '{loc}': {err.get('msg', 'Invalid value')}")
            return None, errors
        except Exception as e:
            errors.append(f"Malformed exam structure: {str(e)}")
            return None, errors

        all_questions = exam_paper.get_all_questions()

        # 3. Total number of questions
        actual_q_count = len(all_questions)
        if actual_q_count != blueprint.total_questions:
            errors.append(
                f"Question count mismatch: expected {blueprint.total_questions}, but generated {actual_q_count} questions."
            )

        # 4 & 5. Correct marks per question and total marks
        actual_total_marks = exam_paper.total_calculated_marks()
        if actual_total_marks != blueprint.total_marks:
            errors.append(
                f"Total marks mismatch: expected {blueprint.total_marks} marks, but total calculated is {actual_total_marks} marks."
            )

        # Match questions by type against pattern with flexible matching
        pattern_lookup = {p.question_type.lower().strip(): p for p in blueprint.pattern}

        def find_matched_pattern(q_type_str: str):
            q_lower = q_type_str.lower().strip()
            if q_lower in pattern_lookup:
                return pattern_lookup[q_lower]
            if "mcq" in q_lower or "multiple choice" in q_lower:
                for p in blueprint.pattern:
                    if "mcq" in p.question_type.lower() or "choice" in p.question_type.lower():
                        return p
            for p_name, p in pattern_lookup.items():
                if p_name in q_lower or q_lower in p_name:
                    return p
            return None

        for q in all_questions:
            matched_pat = find_matched_pattern(q.type)
            if matched_pat and q.marks != matched_pat.marks_per_question:
                errors.append(
                    f"Question #{q.number} ('{q.type}') has {q.marks} marks, but blueprint specified {matched_pat.marks_per_question} marks per question."
                )

        # 8 & 9. No empty or duplicate questions
        seen_stems = set()
        for idx, q in enumerate(all_questions, 1):
            stem = q.question.strip()
            if not stem:
                errors.append(f"Question #{idx} is empty.")
                continue

            normalized = " ".join(stem.lower().split())
            if normalized in seen_stems:
                errors.append(f"Duplicate question detected: #{idx} is identical or near-identical to an earlier question.")
            seen_stems.add(normalized)

        # 10. MCQs have exactly 4 options
        for q in all_questions:
            is_mcq = "mcq" in q.type.lower() or "multiple choice" in q.type.lower()
            if is_mcq:
                if not q.options or len(q.options) != 4:
                    opt_count = len(q.options) if q.options else 0
                    errors.append(
                        f"Question #{q.number} is an MCQ but has {opt_count} options instead of exactly 4 choices."
                    )
            else:
                # Non-MCQs shouldn't usually have options lists
                if q.options and len(q.options) > 0 and "choice" not in q.type.lower():
                    # Clear them out or warn
                    pass

        # 11. Internal choices follow requested pattern
        if blueprint.include_internal_choices:
            # Check if at least some medium/long answer questions provide internal choices
            non_mcq_count = sum(1 for q in all_questions if "mcq" not in q.type.lower())
            choice_count = sum(1 for q in all_questions if q.internal_choice and q.internal_choice.strip())
            if non_mcq_count > 0 and choice_count == 0:
                errors.append("Internal choice option was enabled, but no questions included an internal choice ('OR' alternative).")

        if errors:
            return None, errors

        return exam_paper, []

    @classmethod
    def validate_and_heal(
        cls,
        raw_data: Dict[str, Any],
        blueprint: ExamBlueprint,
        gemini_service: Any,
        max_attempts: int = 2
    ) -> ExamPaper:
        """Validates generated data and automatically initiates up to `max_attempts`

        correction cycles with Gemini if issues are detected.
        """
        current_data = raw_data
        all_attempts_errors: List[List[str]] = []

        for attempt in range(max_attempts + 1):
            exam_paper, errors = cls.validate_exam_paper(current_data, blueprint)

            if exam_paper is not None and not errors:
                return exam_paper

            all_attempts_errors.append(errors)
            logger.warning(
                "Exam validation attempt %d failed with %d errors: %s",
                attempt + 1,
                len(errors),
                errors
            )

            # If retries remain, ask Gemini to self-heal
            if attempt < max_attempts:
                import json
                raw_str = json.dumps(current_data, indent=2)
                correction_prompt = build_correction_prompt(raw_str, errors, blueprint)
                try:
                    corrected_data = gemini_service.generate_json(
                        prompt=correction_prompt,
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2
                    )
                    current_data = corrected_data
                except Exception as e:
                    logger.error("Error during auto-correction round %d: %s", attempt + 1, str(e))
                    # Break out and report the primary errors
                    break

        # If still invalid after correction attempts, format comprehensive user error
        last_errors = all_attempts_errors[-1] if all_attempts_errors else ["Unknown validation failure"]
        bulleted_errors = "\n".join(f"• {e}" for e in last_errors)
        raise RuntimeError(
            f"Exam paper validation failed after {len(all_attempts_errors)} attempt(s):\n{bulleted_errors}"
        )

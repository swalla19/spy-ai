"""Universal prompts for Gemini AI Exam Paper Generation.

Ensures subject-agnostic academic rigor, strict adherence to blueprints,
and JSON schema conformity.
"""

import json
from typing import Dict, Any, List
from models.exam_models import ExamBlueprint, SingleQuestionRegenRequest


SYSTEM_PROMPT = """You are an expert examination paper designer capable of creating academically appropriate examination questions for any subject, discipline, educational level, or topic.

You must strictly follow the supplied examination blueprint.
Do not assume the subject is computer science or any other specific field.
Use the actual subject and syllabus provided by the user.
Generate questions appropriate to the subject.

Follow the requested:
- total marks
- question count
- question types
- marks per question
- difficulty distribution
- topic distribution
- exam duration
- internal-choice requirements
- Bloom's taxonomy requirements if enabled

Do not generate duplicate or near-duplicate questions.
Ensure the final marks exactly match the requested total.
Return ONLY valid, structured JSON matching the required schema. Do not enclose in markdown formatting or backticks if possible, or provide raw JSON that can be parsed directly.
"""


def build_exam_generation_prompt(blueprint: ExamBlueprint) -> str:
    """Constructs the comprehensive generation prompt from an ExamBlueprint."""

    # Format question pattern
    pattern_lines = []
    for item in blueprint.pattern:
        pattern_lines.append(
            f"- Question Type: '{item.question_type}' | Count: {item.count} questions | Marks per Question: {item.marks_per_question} (Subtotal: {item.total_marks} marks)"
        )
    pattern_str = "\n".join(pattern_lines)

    # Format topic weightage if provided
    topic_weight_str = "Intelligently distribute questions across all syllabus units and topics proportionally."
    if blueprint.topic_weights:
        tw_lines = [f"- {t}: {w}%" for t, w in blueprint.topic_weights.items()]
        topic_weight_str = "Strictly adhere to the following topic weightages:\n" + "\n".join(tw_lines)

    options_list = []
    if blueprint.include_answer_key:
        options_list.append("INCLUDE complete, clear answer keys / solutions for all questions (including correct option letter and explanation for MCQs).")
    else:
        options_list.append("Do NOT include answer keys (leave 'answer' field null or omitted).")

    if blueprint.include_internal_choices:
        options_list.append("Provide internal choice ('OR' alternative question) for Long and Medium answer questions in the 'internal_choice' field.")
    else:
        options_list.append("Do not provide internal choices ('internal_choice' should be null).")

    if blueprint.follow_blooms_taxonomy:
        options_list.append("Label each question with its Bloom's Taxonomy cognitive level (Remember, Understand, Apply, Analyze, Evaluate, Create).")
    
    if blueprint.avoid_duplicates:
        options_list.append("Ensure absolute diversity: zero duplicate or near-duplicate questions across all sections.")

    options_str = "\n".join(f"- {opt}" for opt in options_list)

    schema_example = {
        "exam": {
            "title": "UNIVERSITY EXAMINATION",
            "subject": blueprint.subject,
            "duration": blueprint.duration,
            "total_marks": blueprint.total_marks,
            "instructions": [
                "1. Answer all questions according to section guidelines.",
                "2. Figures to the right indicate full marks allocated to each question."
            ]
        },
        "sections": [
            {
                "name": "SECTION A - Multiple Choice Questions",
                "instructions": "Select the correct alternative for each question.",
                "questions": [
                    {
                        "number": 1,
                        "type": "MCQ",
                        "question": "Clear, subject-specific question stem...",
                        "options": [
                            "A. First alternative",
                            "B. Second alternative",
                            "C. Third alternative",
                            "D. Fourth alternative"
                        ],
                        "answer": "A. First alternative - [Detailed explanation]",
                        "marks": 1,
                        "topic": "Specific syllabus topic",
                        "difficulty": "Easy",
                        "bloom_level": "Remember",
                        "internal_choice": None
                    }
                ]
            }
        ]
    }

    prompt = f"""Generate a complete, high-quality university examination paper based on the following blueprint:

==================================================
EXAMINATION SPECIFICATIONS
==================================================
Subject: {blueprint.subject}
Total Marks: {blueprint.total_marks}
Exam Duration: {blueprint.duration}
Total Questions Required: {blueprint.total_questions}

Syllabus / Topics:
\"\"\"
{blueprint.syllabus}
\"\"\"

Question Pattern Specifications:
{pattern_str}

Difficulty Distribution Target:
- Easy: {blueprint.difficulty.easy}%
- Medium: {blueprint.difficulty.medium}%
- Hard: {blueprint.difficulty.hard}%

Topic Distribution Strategy:
{topic_weight_str}

Additional Constraints:
{options_str}

==================================================
STRICT JSON SCHEMA REQUIREMENT
==================================================
Your output must be a single JSON object matching this exact structure:

{json.dumps(schema_example, indent=2)}

IMPORTANT RULES:
1. Every section must group questions by question type or traditional exam sectioning (e.g., Section A: MCQs, Section B: Short Answers, etc.).
2. Sequential question numbering must be maintained from 1 to {blueprint.total_questions}.
3. Every MCQ question MUST contain exactly 4 choices in 'options' prefixed with 'A.', 'B.', 'C.', 'D.'.
4. Non-MCQ questions must have 'options': null.
5. The sum of all questions' marks across all sections MUST EQUAL EXACTLY {blueprint.total_marks}.
6. Total question count across all sections MUST EQUAL EXACTLY {blueprint.total_questions}.
7. Return ONLY valid JSON. Do not include markdown code block quotes (` ```json ` or ` ``` `) around the response.
"""
    return prompt


def build_correction_prompt(raw_response: str, errors: List[str], blueprint: ExamBlueprint) -> str:
    """Builds a targeted correction prompt when validation fails."""
    error_list_str = "\n".join(f"- {err}" for err in errors)
    return f"""The previous JSON output failed validation with the following specific errors:

ERRORS ENCOUNTERED:
{error_list_str}

EXAM BLUEPRINT REQUIREMENTS:
- Subject: {blueprint.subject}
- Total Marks Required: {blueprint.total_marks}
- Total Questions Required: {blueprint.total_questions}
- Question Pattern:
{chr(10).join(f"  * {p.question_type}: {p.count} questions x {p.marks_per_question} marks = {p.total_marks}" for p in blueprint.pattern)}

PREVIOUS GENERATED CONTENT (to be corrected):
\"\"\"
{raw_response[:4000]}
\"\"\"

TASK:
Correct the errors listed above. Make sure the total marks sum to exactly {blueprint.total_marks}, the total question count is {blueprint.total_questions}, all MCQs have 4 options, and all fields match the required schema.

Return ONLY the corrected, complete JSON object.
"""


def build_question_regeneration_prompt(req: SingleQuestionRegenRequest) -> str:
    """Prompt for regenerating a single question while retaining its parameters."""
    options_instruction = ""
    if "MCQ" in req.question_type.upper():
        options_instruction = "Must provide exactly 4 distinct options ('A.', 'B.', 'C.', 'D.')."
    else:
        options_instruction = "'options' should be null."

    answer_instruction = "Include complete answer/solution." if req.include_answer_key else "Leave 'answer' as null."

    return f"""You are an expert examination paper designer.
Regenerate a SINGLE fresh examination question to replace an existing question.

REQUIREMENTS:
- Subject: {req.subject}
- Topic: {req.topic}
- Question Type: {req.question_type}
- Marks: {req.marks}
- Difficulty: {req.difficulty}
- Bloom's Taxonomy Level: {req.bloom_level or 'Appropriate to question level'}
- {options_instruction}
- {answer_instruction}

EXISTING QUESTION TO REPLACE (Do NOT reuse or lightly rephrase this):
\"\"\"
{req.existing_question}
\"\"\"

Create an entirely new, creative, academically sound question testing the same topic at the specified difficulty and mark level.

Return ONLY a valid JSON object representing the single question with this schema:
{{
  "type": "{req.question_type}",
  "question": "New question statement...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."] or null,
  "answer": "Solution..." or null,
  "marks": {req.marks},
  "topic": "{req.topic}",
  "difficulty": "{req.difficulty}",
  "bloom_level": "{req.bloom_level or 'Apply'}",
  "internal_choice": null
}}
"""

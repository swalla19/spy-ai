"""Pydantic models for the AI Exam Paper Generator.

Defines schemas for examination structures, questions, sections,
patterns, blueprints, and validation requirements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class Question(BaseModel):
    """Represents an individual examination question."""
    number: int = Field(..., description="Sequential question number across or within paper")
    type: str = Field(..., description="Type of question e.g. MCQ, Short Answer, Medium Answer, Long Answer")
    question: str = Field(..., description="The complete question statement or prompt")
    options: Optional[List[str]] = Field(
        default=None,
        description="List of 4 options for MCQs (e.g. ['A. ...', 'B. ...', 'C. ...', 'D. ...']) or None for other types"
    )
    answer: Optional[str] = Field(
        default=None,
        description="Correct answer, solution key, or evaluation rubric points"
    )
    marks: int = Field(..., ge=1, description="Marks allocated to this question")
    topic: str = Field(..., description="Subject topic or syllabus unit this question addresses")
    difficulty: str = Field(..., description="Difficulty level: Easy, Medium, or Hard")
    bloom_level: Optional[str] = Field(
        default=None,
        description="Bloom's Taxonomy category (e.g., Remember, Understand, Apply, Analyze, Evaluate, Create)"
    )
    internal_choice: Optional[str] = Field(
        default=None,
        description="Alternative question text if internal choice is offered ('OR' question)"
    )

    @field_validator("question")
    @classmethod
    def validate_question_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question text cannot be empty.")
        return v.strip()


class Section(BaseModel):
    """Represents a section in an examination paper."""
    name: str = Field(..., description="Section title e.g. 'SECTION A - Multiple Choice Questions'")
    instructions: Optional[str] = Field(
        default=None,
        description="Specific instructions for this section e.g. 'Answer all questions. Each carries 1 mark.'"
    )
    questions: List[Question] = Field(default_factory=list, description="Questions belonging to this section")


class ExamMetadata(BaseModel):
    """Metadata regarding the overall examination paper."""
    title: str = Field(default="UNIVERSITY EXAMINATION", description="Header / Title of the examination")
    subject: str = Field(..., description="Subject of the examination")
    duration: str = Field(..., description="Total time allowed e.g. '2 Hours'")
    total_marks: int = Field(..., ge=1, description="Maximum marks for the examination")
    instructions: List[str] = Field(
        default_factory=lambda: [
            "1. Answer all questions according to section instructions.",
            "2. Figures to the right indicate full marks.",
            "3. Use of non-programmable calculators is permitted where applicable."
        ],
        description="General instructions for the student"
    )


class ExamPaper(BaseModel):
    """Complete examination paper response structure."""
    exam: ExamMetadata = Field(..., description="Exam metadata and general instructions")
    sections: List[Section] = Field(default_factory=list, description="All sections in the examination paper")

    def total_calculated_marks(self) -> int:
        """Sum marks across all questions in all sections."""
        return sum(q.marks for s in self.sections for q in s.questions)

    def total_question_count(self) -> int:
        """Count total questions across all sections."""
        return sum(len(s.questions) for s in self.sections)

    def get_all_questions(self) -> List[Question]:
        """Flat list of all questions."""
        questions = []
        for s in self.sections:
            questions.extend(s.questions)
        return questions


# ==========================================
# Configuration & Blueprint Models
# ==========================================

class QuestionPatternItem(BaseModel):
    """A configured question pattern row."""
    question_type: str = Field(..., description="Question type name e.g. MCQ, Short Answer")
    count: int = Field(..., ge=1, description="Number of questions of this type")
    marks_per_question: int = Field(..., ge=1, description="Marks assigned to each question of this type")

    @property
    def total_marks(self) -> int:
        return self.count * self.marks_per_question


class DifficultyDistribution(BaseModel):
    """Target percentage difficulty distribution."""
    easy: int = Field(default=30, ge=0, le=100)
    medium: int = Field(default=50, ge=0, le=100)
    hard: int = Field(default=20, ge=0, le=100)

    @model_validator(mode="after")
    def validate_sum(self) -> "DifficultyDistribution":
        total = self.easy + self.medium + self.hard
        if total == 0:
            self.easy, self.medium, self.hard = 30, 50, 20
        elif total != 100:
            # Normalize to 100%
            factor = 100.0 / total
            self.easy = int(round(self.easy * factor))
            self.medium = int(round(self.medium * factor))
            self.hard = 100 - (self.easy + self.medium)
        return self


class ExamBlueprint(BaseModel):
    """Formal structured blueprint generated prior to Gemini examination creation."""
    subject: str
    syllabus: str
    total_marks: int
    duration: str
    difficulty: DifficultyDistribution
    pattern: List[QuestionPatternItem]
    total_questions: int
    calculated_marks: int
    topic_weights: Optional[Dict[str, int]] = None
    include_answer_key: bool = True
    include_internal_choices: bool = False
    follow_blooms_taxonomy: bool = True
    avoid_duplicates: bool = True


class SingleQuestionRegenRequest(BaseModel):
    """Request payload to regenerate a specific individual question."""
    subject: str
    topic: str
    question_type: str
    marks: int
    difficulty: str
    bloom_level: Optional[str] = None
    existing_question: str
    include_answer_key: bool = True

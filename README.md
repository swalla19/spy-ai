# 🎓 AI Exam Paper Generator

> Universal, academically rigorous examination paper generator for any subject using Google Gemini AI, Pydantic validation, dynamic pattern builders, and ReportLab PDF synthesis.

---

## 1. Project Description

The **AI Exam Paper Generator** is a universal, subject-agnostic academic paper creation engine. The architecture adheres to a strict separation of concerns:
- **Google Gemini AI** (`gemini-3.6-flash`) acts as the subject-matter expert across humanities, sciences, engineering, medicine, and law.
- **Python & Pydantic** govern the pedagogical structure, mark balancing, question counts, option verification, and validation rules.
- **ReportLab** compiles publication-grade university examination PDFs with custom headers, section partitioning, right-aligned mark badges, and confidential answer keys.

---

## 2. Key Features

- **Universal Discipline Support**: Generates exams for Physics, Compiler Construction, World History, Macroeconomics, Molecular Biology, Law, or any custom syllabus without subject-specific hardcoding.
- **Dynamic Question Pattern Builder**: Fully configurable question types (MCQ, Short Answer, Medium Answer, Long Answer, Problem/Derivation), counts, and marks per question.
- **Real-Time Blueprint Validation**: Compares calculated pattern marks against total target marks before invoking AI, preventing wasted API tokens.
- **Multi-Stage Validation & Self-Healing Loop**: Automatically validates question counts, mark sums, MCQ option count (4 choices), and duplicate absence. Automatically performs up to 2 correction rounds if any schema deviation is detected.
- **In-Place Single-Question Regeneration**: Allows educators to swap out an individual question while retaining its exact topic, difficulty, question type, and mark allocation.
- **Professional PDF Generation**: Generates university-grade printable PDFs with run-time headers, page counts ("Page X of Y"), and an optional separate evaluation scheme/answer key.
- **Bloom's Taxonomy & Difficulty Distribution**: Configurable Easy / Medium / Hard ratios and cognitive skill levels (Remember, Understand, Apply, Analyze, Evaluate, Create).
- **Modern Gradio Web UI**: Two-column layout, live preset loaders, status notifications, and raw JSON inspection for debugging.

---

## 3. Architecture

```
                       +-----------------------------+
                       |    User Configuration UI    |
                       |         (Gradio 6)          |
                       +--------------+--------------+
                                      |
                                      v
                       +-----------------------------+
                       |     Blueprint Validator     |
                       |  (Marks tally & consistency)|
                       +--------------+--------------+
                                      |
                                      v
                       +-----------------------------+
                       |       Gemini Service        |
                       | (Structured JSON Generation)|
                       +--------------+--------------+
                                      |
                         Raw JSON     v
                       +-----------------------------+
                       |      Pydantic Validator     |
                       |  (11 Structural Invariants) |
                       +-------+--------------+------+
                               |              |
                      Invalid  |              | Valid
                   (Retries<=2)|              v
                               |      +---------------------+
                               +----->|  Auto-Correction    |
                                      |  Feedback Prompt    |
                                      +---------------------+
                                              |
                                              v
                              +-------------------------------+
                              |    Exam Paper Render (HTML)   |
                              |   & ReportLab PDF Generator   |
                              +-------------------------------+
```

---

## 4. Project Structure

```
spy ai/
├── .env                       # Active environment configuration with Gemini API key
├── .env.example               # Template environment configuration
├── requirements.txt           # Project dependencies
├── README.md                  # Complete documentation
├── app.py                     # Main Gradio application launch script
│
├── models/
│   ├── __init__.py
│   └── exam_models.py         # Pydantic schemas (Question, Section, ExamPaper, Blueprint)
│
├── services/
│   ├── __init__.py
│   ├── gemini_service.py      # Google GenAI client (google-genai) wrapper
│   ├── exam_generator.py      # Blueprint calculator, generation orchestrator, regenerator
│   └── validator.py           # Multi-stage validator with self-healing correction loop
│
├── utils/
│   ├── __init__.py
│   ├── prompts.py             # Universal academic system and user prompts
│   └── pdf_generator.py       # ReportLab PDF engine (university examination format)
│
└── output/
    └── generated_papers/      # Storage directory for compiled PDF examination papers
```

---

## 5. Getting a Gemini API Key

1. Navigate to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **Get API key** and generate a new key.
4. Copy the API key string.

---

## 6. Environment Setup (`.env`)

Create or update `.env` in the root directory:

```env
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Configurable Gemini Model (default: gemini-3.6-flash)
GEMINI_MODEL=gemini-3.6-flash
```

---

## 7. Installing Requirements

Ensure Python 3.10+ is installed, then run:

```bash
pip install -r requirements.txt
```

Core dependencies:
- `gradio>=5.0.0`
- `google-genai>=2.0.0`
- `pydantic>=2.0.0`
- `reportlab>=4.0.0`
- `python-dotenv>=1.0.0`

---

## 8. Running the Application

Launch the local web server:

```bash
python app.py
```

Or using the Python launcher on Windows:

```bash
py app.py
```

Then open your browser at:
```
http://127.0.0.1:7860
```

---

## 9. Example Usage

### Example A: Fast Load with Built-in Presets
1. Select a subject from the **Quick Load Subject Presets** dropdown:
   - *Compiler Construction (60 Marks)*
   - *Physics: Thermodynamics & Optics (50 Marks)*
   - *World History: 1914 - 1990 (40 Marks)*
   - *Principles of Macroeconomics (30 Marks)*
2. Click **Load Preset**.
3. Click **Generate Blueprint** to inspect the calculated question distribution.
4. Click **🚀 Generate Exam Paper**.
5. Inspect the rendered exam paper, review the answer keys, and click **📥 Download PDF**.

### Example B: Custom Exam Configuration
1. **Subject**: Enter any discipline (e.g., `Organic Chemistry`, `Corporate Law`, `Calculus III`).
2. **Syllabus**: Paste chapters or specific lecture topics.
3. **Total Marks**: Enter e.g. `100`.
4. **Question Pattern**: Adjust counts and marks (e.g. 20 MCQs × 1M = 20M, 5 Short × 4M = 20M, 6 Medium × 5M = 30M, 3 Long × 10M = 30M).
5. Ensure calculated marks match the total marks exactly.
6. Click **Generate Exam Paper**.

### Example C: In-Place Question Regeneration
1. If question #3 isn't ideal, scroll to the **Regenerate Specific Question** section.
2. Select `Q3: ...` from the dropdown.
3. Click **Regenerate Selected**.
4. Gemini will create a fresh question testing the same topic and difficulty, updating both the paper view and the downloadable PDF without modifying any other question.

---

## 10. Error Handling Matrix

| Issue | UI Handling |
|---|---|
| **Missing API Key** | Displays clear alert guiding the user to configure `.env`. |
| **Marks Mismatch** | Halts generation before API call, showing exact mark delta and fix instructions. |
| **Invalid Schema / Missing Options** | Triggers automated self-healing feedback loop with Gemini (up to 2 attempts). |
| **Rate Limit / Resource Exhaustion** | Displays friendly rate-limit notice asking user to wait briefly. |
| **Empty Inputs** | Warns user with field-specific guidance. |

---

## 11. Future Improvements

- [ ] PDF Syllabus parsing (upload textbook / course syllabus PDF and auto-extract topics).
- [ ] Multiple randomized paper sets (Set A, Set B, Set C) with shuffled questions and altered numbers.
- [ ] Question bank export (QTI / Moodle XML / Canvas export).
- [ ] Student examination mode with automated evaluation against the generated rubric.
- [ ] LaTeX / MathJax rendering for complex mathematical equations.

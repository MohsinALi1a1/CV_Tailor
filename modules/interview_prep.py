"""
CV Tailor — Interview Preparation Generator
=============================================
Generates likely interview questions and STAR-method answer scaffolds
based on a job description and candidate's resume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from utils.api_clients import get_claude_client


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Question Banks (used when AI is unavailable)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEHAVIORAL_QUESTIONS: list[str] = [
    "Tell me about a time you faced a difficult problem at work and how you solved it.",
    "Describe a situation where you had to work with a difficult team member.",
    "Tell me about a time you failed and what you learned from it.",
    "Describe a time when you had to make a decision with incomplete information.",
    "Tell me about a project you led from start to finish.",
    "Describe a situation where you had to meet a tight deadline.",
    "Tell me about a time you had to learn something new quickly.",
    "Describe how you've handled disagreements with your manager.",
    "Tell me about a time you took initiative beyond your role.",
    "Describe a situation where you had to influence others without authority.",
    "Tell me about your biggest professional achievement.",
    "Describe a time when you received critical feedback. How did you respond?",
    "Tell me about a time you had to prioritize competing demands.",
    "Describe a situation where you went above and beyond for a customer/stakeholder.",
    "Tell me about a time you had to adapt to a major change.",
]

LEADERSHIP_QUESTIONS: list[str] = [
    "How do you motivate a team that's facing burnout?",
    "Tell me about a time you had to make an unpopular decision.",
    "How do you handle underperforming team members?",
    "Describe your leadership style and give an example.",
    "Tell me about a time you mentored someone.",
    "How do you build trust with a new team?",
    "Describe a time you had to deliver difficult news to your team.",
]

TECHNICAL_QUESTIONS_BY_ROLE: dict[str, list[str]] = {
    "software_engineering": [
        "Walk me through your approach to designing a scalable web service.",
        "How do you decide between SQL and NoSQL databases?",
        "Describe your experience with CI/CD pipelines.",
        "How do you approach debugging a production issue?",
        "Explain a design pattern you've used recently and why.",
        "How do you ensure code quality in your team?",
        "Walk me through your code review process.",
        "How do you balance technical debt vs. new features?",
        "Describe your testing strategy (unit, integration, e2e).",
        "How would you handle a memory leak in production?",
    ],
    "data_science": [
        "Walk me through a machine learning project end-to-end.",
        "How do you handle imbalanced datasets?",
        "Explain bias-variance tradeoff with an example.",
        "How do you decide which evaluation metric to use?",
        "Describe a time when your model didn't perform as expected. What did you do?",
        "How do you explain a complex model to non-technical stakeholders?",
        "Walk me through how you'd build a recommendation system.",
        "How do you handle missing data?",
        "Explain feature engineering with examples from your work.",
        "How do you stay current with ML research?",
    ],
    "data_engineering": [
        "Walk me through a data pipeline you've built.",
        "How do you ensure data quality?",
        "Describe your experience with batch vs. streaming.",
        "How do you handle schema evolution?",
        "Explain your approach to data modeling for analytics.",
        "How do you optimize a slow SQL query?",
        "Describe a time you had to debug a broken pipeline at 3am.",
        "How do you handle PII and data governance?",
    ],
    "devops_sre": [
        "Walk me through your incident response process.",
        "How do you decide what to monitor and alert on?",
        "Describe a time you improved system reliability significantly.",
        "How do you approach capacity planning?",
        "Explain your IaC strategy and tools used.",
        "How do you handle on-call burnout in your team?",
        "Walk me through a post-mortem you led.",
        "How do you balance velocity vs. stability?",
    ],
    "product_management": [
        "Walk me through how you prioritize a roadmap.",
        "Tell me about a product you launched that failed.",
        "How do you decide what NOT to build?",
        "Describe how you work with engineering and design.",
        "Walk me through a product spec you've written.",
        "How do you measure product success?",
        "Tell me about a time you used data to change direction.",
        "How do you handle stakeholders with conflicting priorities?",
    ],
    "design_ux": [
        "Walk me through your design process.",
        "Tell me about a design you're most proud of.",
        "How do you handle feedback you disagree with?",
        "Describe a time user research changed your design.",
        "How do you balance business needs and user needs?",
        "Walk me through a design system you've contributed to.",
        "How do you advocate for accessibility?",
    ],
    "marketing": [
        "Walk me through a successful campaign you led.",
        "How do you measure ROI on brand campaigns?",
        "Describe your approach to A/B testing.",
        "How do you allocate budget across channels?",
        "Tell me about a campaign that underperformed. What did you do?",
        "How do you stay current with marketing trends?",
    ],
    "sales": [
        "Walk me through your sales process.",
        "Tell me about your largest deal close.",
        "How do you handle rejection?",
        "Describe a time you turned around a stalled deal.",
        "How do you prospect new accounts?",
        "Walk me through how you handle objections.",
        "How do you manage your pipeline?",
    ],
}

QUESTIONS_TO_ASK_INTERVIEWER: list[str] = [
    "What does success look like in this role in the first 6 months?",
    "What are the biggest challenges the team is facing right now?",
    "How would you describe the team culture?",
    "What does career growth look like for someone in this position?",
    "How is performance measured and reviewed?",
    "What's the team's approach to work-life balance?",
    "Can you tell me about the team structure and who I'd be working with?",
    "What are the company's biggest priorities for the next year?",
    "What do you enjoy most about working here?",
    "What's the next step in the interview process?",
]


@dataclass
class InterviewQuestion:
    question: str
    category: str  # behavioral | technical | leadership | situational | role-specific
    suggested_star: str = ""  # AI-generated STAR-method scaffold
    keywords_to_mention: list[str] = field(default_factory=list)


@dataclass
class InterviewPrepResult:
    role: str = ""
    company: str = ""
    behavioral: list[InterviewQuestion] = field(default_factory=list)
    technical: list[InterviewQuestion] = field(default_factory=list)
    role_specific: list[InterviewQuestion] = field(default_factory=list)
    leadership: list[InterviewQuestion] = field(default_factory=list)
    questions_to_ask: list[str] = field(default_factory=list)
    preparation_tips: list[str] = field(default_factory=list)
    ai_powered: bool = False

    def to_dict(self) -> dict[str, Any]:
        def _q(qs: list[InterviewQuestion]) -> list[dict[str, Any]]:
            return [
                {
                    "question": q.question,
                    "category": q.category,
                    "suggested_star": q.suggested_star,
                    "keywords_to_mention": q.keywords_to_mention,
                }
                for q in qs
            ]
        return {
            "role": self.role,
            "company": self.company,
            "behavioral": _q(self.behavioral),
            "technical": _q(self.technical),
            "role_specific": _q(self.role_specific),
            "leadership": _q(self.leadership),
            "questions_to_ask": self.questions_to_ask,
            "preparation_tips": self.preparation_tips,
            "ai_powered": self.ai_powered,
        }


def _detect_role_key(job_description: str) -> str:
    """Best-effort role classification for question selection."""
    try:
        from modules.industry_intel import detect_industry
        analysis = detect_industry(job_description)
        return analysis.primary_industry or "software_engineering"
    except Exception:
        return "software_engineering"


def generate_interview_prep(
    resume_text: str,
    job_description: str,
    role: str = "",
    company: str = "",
    use_ai: bool = True,
    questions_per_category: int = 5,
) -> InterviewPrepResult:
    """Generate interview preparation material.

    Args:
        resume_text: Candidate's resume.
        job_description: Target job description.
        role: Target role title (optional).
        company: Target company name (optional).
        use_ai: Use Claude for AI-powered STAR scaffolds.
        questions_per_category: Number of questions per category.

    Returns:
        InterviewPrepResult.
    """
    role_key = _detect_role_key(job_description)
    technical_bank = TECHNICAL_QUESTIONS_BY_ROLE.get(role_key, TECHNICAL_QUESTIONS_BY_ROLE["software_engineering"])

    n = max(1, min(questions_per_category, 15))
    behavioral = [
        InterviewQuestion(question=q, category="behavioral")
        for q in BEHAVIORAL_QUESTIONS[:n]
    ]
    technical = [
        InterviewQuestion(question=q, category="technical")
        for q in technical_bank[:n]
    ]
    leadership = [
        InterviewQuestion(question=q, category="leadership")
        for q in LEADERSHIP_QUESTIONS[:min(3, n)]
    ]

    role_specific: list[InterviewQuestion] = []
    tips: list[str] = []

    # Try AI for role-specific questions and STAR scaffolds
    if use_ai:
        try:
            client = get_claude_client()
            ai_questions, ai_tips = _ai_generate_questions(
                client, resume_text, job_description, role, company
            )
            role_specific = ai_questions
            tips = ai_tips
            ai_powered = True
        except Exception:
            ai_powered = False
            tips = _default_tips(role, company)
    else:
        ai_powered = False
        tips = _default_tips(role, company)

    return InterviewPrepResult(
        role=role,
        company=company,
        behavioral=behavioral,
        technical=technical,
        role_specific=role_specific,
        leadership=leadership,
        questions_to_ask=QUESTIONS_TO_ASK_INTERVIEWER.copy(),
        preparation_tips=tips,
        ai_powered=ai_powered,
    )


def _ai_generate_questions(
    client: Any,
    resume_text: str,
    job_description: str,
    role: str,
    company: str,
) -> tuple[list[InterviewQuestion], list[str]]:
    """Use Claude to generate tailored questions + STAR-method tips."""
    prompt = f"""You are an expert interview coach with 20+ years preparing candidates for top tech and business roles.

# CANDIDATE RESUME
{resume_text[:4000]}

# TARGET JOB DESCRIPTION
{job_description[:4000]}

# TARGET ROLE
Role: {role or "(see job description)"}
Company: {company or "(unspecified)"}

# YOUR TASK
Generate a comprehensive interview prep package in this EXACT format:

ROLE_SPECIFIC_QUESTIONS:
1. [Question tailored to this specific JD, mentioning a key responsibility]
2. [Another question probing a specific technical/business requirement]
3. [Question about a specific skill or experience listed in JD]
4. [Question challenging the candidate on a gap between resume and JD]
5. [Question about company-specific knowledge or industry trends]
6. [Question about a project type mentioned in the JD]
7. [Question about handling a scenario this role would face]

PREPARATION_TIPS:
- [Specific tip about gaps to address based on resume vs JD comparison]
- [Tip about which experiences to highlight from this resume]
- [Tip about company-specific research to do]
- [Tip about the most likely "deal-breaker" topics]
- [Tip about how to frame weaknesses for this role]
- [Tip about closing the interview strongly]

Output ONLY the formatted sections above. No preamble, no closing notes."""

    response = client.client.messages.create(
        model=client.model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text if response.content else ""

    questions: list[InterviewQuestion] = []
    tips: list[str] = []
    current = None
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        up = line.upper()
        if up.startswith("ROLE_SPECIFIC_QUESTIONS"):
            current = "questions"
            continue
        if up.startswith("PREPARATION_TIPS"):
            current = "tips"
            continue
        if current == "questions":
            # Strip numbering like "1." or "1)"
            cleaned = line.lstrip("0123456789.) ").strip()
            if cleaned:
                questions.append(InterviewQuestion(
                    question=cleaned, category="role-specific"
                ))
        elif current == "tips":
            cleaned = line.lstrip("-*•").strip()
            if cleaned:
                tips.append(cleaned)

    return questions, tips


def _default_tips(role: str, company: str) -> list[str]:
    tips = [
        "Research the company's mission, recent news, and core products before the interview.",
        "Prepare 3-5 specific STAR-method stories from your resume that map to common behavioral questions.",
        "Review the job description and prepare an example of how you've delivered on each major responsibility.",
        "Practice explaining technical concepts in simple, business-friendly language.",
        "Prepare 3-5 thoughtful questions to ask the interviewer (shows genuine interest).",
        "Run a mock interview the day before, ideally with a peer or coach.",
        "Plan your outfit, route, and tech setup (for virtual) 24 hours in advance.",
        "Have water, your resume, the JD, and a notepad ready at the interview.",
        "Send a personalized thank-you email within 24 hours after the interview.",
    ]
    if company:
        tips.insert(0, f"Research {company}'s competitors, recent press releases, and engineering blog (if applicable).")
    if role:
        tips.insert(0, f"Be ready to articulate why you specifically want THIS '{role}' role, not just any role.")
    return tips


def generate_star_scaffold(
    question: str,
    resume_text: str,
    use_ai: bool = True,
) -> str:
    """Generate a STAR-method (Situation, Task, Action, Result) scaffold for a question."""
    if use_ai:
        try:
            client = get_claude_client()
            prompt = f"""You are an interview coach. The candidate's resume:

{resume_text[:3500]}

INTERVIEW QUESTION: {question}

Provide a STAR-method answer scaffold using ONE specific experience from this resume.
Format EXACTLY as:

SITUATION: [1-2 sentence context]
TASK: [1 sentence on the responsibility]
ACTION: [2-3 sentences on specific steps the candidate took]
RESULT: [1-2 sentences with quantified outcomes]

Be specific. Use real numbers/names from the resume where possible."""

            response = client.client.messages.create(
                model=client.model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        except Exception:
            pass

    return (
        "SITUATION: [Describe the context, project, or challenge]\n"
        "TASK: [Explain your specific responsibility]\n"
        "ACTION: [Detail the steps you personally took]\n"
        "RESULT: [Share the measurable outcome and impact]"
    )

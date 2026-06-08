"""
CV Tailor — Industry Intelligence Module
=========================================
Detects the industry/domain of a job description and provides industry-specific
keyword banks, terminology, and ATS optimization tips.

Based on research from BLS (Bureau of Labor Statistics), LinkedIn Talent Insights,
and industry hiring reports (2024-2026).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Industry Keyword Banks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INDUSTRY_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "software_engineering": {
        "core": [
            "python", "java", "javascript", "typescript", "c++", "c#", "go",
            "rust", "react", "angular", "vue", "node.js", "django", "flask",
            "spring", "rest", "graphql", "microservices", "git", "github",
            "agile", "scrum", "tdd", "ci/cd", "docker", "kubernetes",
        ],
        "tools": [
            "jira", "confluence", "vs code", "intellij", "postman", "swagger",
            "jenkins", "github actions", "gitlab", "linux", "bash",
        ],
        "soft": [
            "problem solving", "collaboration", "code review", "mentoring",
            "technical leadership", "system design", "architecture",
        ],
        "metrics": [
            "uptime", "latency", "throughput", "code coverage", "deployment frequency",
            "mttr", "sla", "performance optimization",
        ],
    },
    "data_science": {
        "core": [
            "python", "r", "sql", "machine learning", "deep learning", "statistics",
            "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
            "jupyter", "data analysis", "data visualization", "feature engineering",
            "predictive modeling", "regression", "classification", "clustering",
            "neural networks", "nlp", "computer vision",
        ],
        "tools": [
            "tableau", "power bi", "looker", "snowflake", "databricks", "spark",
            "airflow", "dbt", "mlflow", "kubeflow", "sagemaker", "vertex ai",
            "hugging face", "langchain", "weights & biases",
        ],
        "soft": [
            "analytical thinking", "statistical analysis", "hypothesis testing",
            "experimentation", "a/b testing", "business acumen", "storytelling",
        ],
        "metrics": [
            "accuracy", "precision", "recall", "f1 score", "auc", "roc",
            "mae", "rmse", "p-value", "confidence interval",
        ],
    },
    "data_engineering": {
        "core": [
            "python", "sql", "scala", "java", "etl", "elt", "data pipeline",
            "data warehouse", "data lake", "big data", "spark", "kafka",
            "airflow", "hadoop", "snowflake", "bigquery", "redshift",
            "postgresql", "mongodb", "cassandra", "data modeling",
        ],
        "tools": [
            "dbt", "fivetran", "airbyte", "stitch", "databricks", "emr",
            "kinesis", "pub/sub", "glue", "lambda", "step functions",
        ],
        "soft": [
            "data quality", "data governance", "scalability", "reliability",
            "stakeholder management",
        ],
        "metrics": [
            "throughput", "latency", "data freshness", "data quality score",
            "pipeline reliability", "cost optimization",
        ],
    },
    "devops_sre": {
        "core": [
            "docker", "kubernetes", "terraform", "ansible", "jenkins",
            "ci/cd", "aws", "azure", "gcp", "linux", "bash", "python",
            "go", "helm", "prometheus", "grafana", "datadog", "elk",
            "microservices", "service mesh", "istio",
        ],
        "tools": [
            "argocd", "spinnaker", "circleci", "github actions", "gitlab ci",
            "pulumi", "vault", "consul", "nomad", "packer",
        ],
        "soft": [
            "incident response", "on-call", "post-mortems", "automation",
            "infrastructure as code", "reliability engineering",
        ],
        "metrics": [
            "uptime", "sli", "slo", "sla", "mttr", "mtbf", "error budget",
            "deployment frequency", "lead time", "change failure rate",
        ],
    },
    "product_management": {
        "core": [
            "product strategy", "roadmap", "user research", "a/b testing",
            "okrs", "kpis", "agile", "scrum", "user stories", "wireframes",
            "prototyping", "stakeholder management", "go-to-market", "gtm",
            "product launch", "competitive analysis", "market research",
        ],
        "tools": [
            "jira", "confluence", "asana", "figma", "miro", "mixpanel",
            "amplitude", "google analytics", "tableau", "sql", "notion",
            "productboard", "aha", "linear",
        ],
        "soft": [
            "communication", "leadership", "cross-functional", "prioritization",
            "data-driven", "customer obsession", "strategic thinking",
        ],
        "metrics": [
            "dau", "mau", "retention", "churn", "ltv", "cac", "conversion rate",
            "nps", "csat", "activation rate", "engagement",
        ],
    },
    "design_ux": {
        "core": [
            "ui design", "ux design", "user research", "wireframing", "prototyping",
            "usability testing", "design systems", "interaction design",
            "visual design", "information architecture", "user journey",
            "personas", "accessibility", "wcag", "responsive design",
        ],
        "tools": [
            "figma", "sketch", "adobe xd", "photoshop", "illustrator",
            "after effects", "principle", "framer", "invision", "miro",
            "zeplin", "abstract",
        ],
        "soft": [
            "empathy", "creativity", "collaboration", "design thinking",
            "storytelling", "presentation",
        ],
        "metrics": [
            "task completion rate", "time on task", "error rate", "sus score",
            "nps", "conversion rate", "engagement",
        ],
    },
    "marketing": {
        "core": [
            "seo", "sem", "content marketing", "email marketing", "social media",
            "ppc", "google ads", "facebook ads", "linkedin ads", "campaign management",
            "marketing automation", "lead generation", "conversion optimization",
            "brand strategy", "growth marketing", "demand generation", "abm",
            "account based marketing",
        ],
        "tools": [
            "hubspot", "marketo", "salesforce", "mailchimp", "klaviyo",
            "google analytics", "ga4", "semrush", "ahrefs", "moz",
            "hootsuite", "buffer", "canva", "wordpress", "hotjar",
        ],
        "soft": [
            "creativity", "communication", "analytical", "storytelling",
            "project management", "cross-functional collaboration",
        ],
        "metrics": [
            "ctr", "cpc", "cpa", "cpm", "roas", "roi", "conversion rate",
            "open rate", "click rate", "engagement rate", "mql", "sql",
            "pipeline", "attribution",
        ],
    },
    "sales": {
        "core": [
            "b2b sales", "b2c sales", "saas sales", "enterprise sales",
            "account management", "lead generation", "prospecting", "cold calling",
            "consultative selling", "solution selling", "spin selling",
            "miller heiman", "challenger sale", "negotiation", "contract negotiation",
            "pipeline management", "forecasting", "quota attainment",
        ],
        "tools": [
            "salesforce", "hubspot", "outreach", "salesloft", "gong", "chorus",
            "linkedin sales navigator", "zoominfo", "apollo", "drift", "calendly",
        ],
        "soft": [
            "relationship building", "active listening", "objection handling",
            "presentation", "communication", "resilience",
        ],
        "metrics": [
            "quota attainment", "arr", "mrr", "win rate", "deal size",
            "sales cycle", "pipeline velocity", "close rate", "churn",
            "expansion revenue", "nrr",
        ],
    },
    "finance": {
        "core": [
            "financial modeling", "valuation", "dcf", "lbo", "m&a",
            "financial analysis", "forecasting", "budgeting", "variance analysis",
            "fp&a", "accounting", "gaap", "ifrs", "audit", "risk management",
            "portfolio management", "equity research", "fixed income",
            "derivatives", "investment banking", "private equity", "venture capital",
        ],
        "tools": [
            "excel", "bloomberg terminal", "factset", "capital iq", "thomson reuters",
            "sap", "oracle", "quickbooks", "netsuite", "workday", "hyperion",
            "tableau", "power bi", "sql", "python", "r",
        ],
        "soft": [
            "analytical", "attention to detail", "communication", "business acumen",
            "ethical", "discretion",
        ],
        "metrics": [
            "roi", "irr", "npv", "ebitda", "p&l", "gross margin", "operating margin",
            "cash flow", "working capital", "debt-to-equity",
        ],
    },
    "healthcare": {
        "core": [
            "patient care", "clinical", "medical records", "ehr", "emr",
            "hipaa", "phi", "icd-10", "cpt", "hl7", "fhir",
            "medical terminology", "anatomy", "pharmacology", "diagnostics",
            "treatment planning", "case management", "patient assessment",
            "clinical research", "evidence-based practice",
        ],
        "tools": [
            "epic", "cerner", "meditech", "allscripts", "athenahealth",
            "nextgen", "ecw", "rxnt", "practice fusion",
        ],
        "soft": [
            "empathy", "compassion", "communication", "teamwork", "critical thinking",
            "decision making", "cultural competency",
        ],
        "metrics": [
            "patient satisfaction", "hcahps", "readmission rate", "mortality rate",
            "length of stay", "wait time", "compliance rate", "outcomes",
        ],
    },
    "education": {
        "core": [
            "curriculum development", "lesson planning", "classroom management",
            "differentiated instruction", "assessment", "iep", "504 plan",
            "student engagement", "pedagogy", "learning outcomes",
            "blended learning", "online learning", "lms",
        ],
        "tools": [
            "google classroom", "canvas", "blackboard", "moodle", "schoology",
            "zoom", "microsoft teams", "kahoot", "nearpod", "seesaw",
        ],
        "soft": [
            "patience", "communication", "creativity", "adaptability",
            "empathy", "leadership", "collaboration",
        ],
        "metrics": [
            "student performance", "graduation rate", "attendance rate",
            "engagement", "assessment scores", "parent satisfaction",
        ],
    },
    "human_resources": {
        "core": [
            "talent acquisition", "recruiting", "sourcing", "onboarding",
            "performance management", "employee engagement", "compensation",
            "benefits", "payroll", "hris", "ats", "diversity equity inclusion",
            "dei", "employee relations", "labor law", "compliance",
            "succession planning", "organizational development",
        ],
        "tools": [
            "workday", "bamboohr", "adp", "ultipro", "greenhouse", "lever",
            "icims", "smartrecruiters", "linkedin recruiter", "indeed",
            "culture amp", "lattice", "15five",
        ],
        "soft": [
            "communication", "empathy", "discretion", "negotiation",
            "conflict resolution", "active listening",
        ],
        "metrics": [
            "time to hire", "cost per hire", "quality of hire", "retention rate",
            "turnover rate", "employee nps", "engagement score",
            "diversity metrics", "promotion rate",
        ],
    },
    "cybersecurity": {
        "core": [
            "network security", "application security", "cloud security",
            "penetration testing", "vulnerability assessment", "incident response",
            "siem", "soc", "threat hunting", "malware analysis", "forensics",
            "encryption", "pki", "iam", "zero trust", "owasp",
            "compliance", "iso 27001", "nist", "soc 2", "pci dss",
        ],
        "tools": [
            "splunk", "qradar", "crowdstrike", "sentinelone", "carbon black",
            "wireshark", "metasploit", "burp suite", "nessus", "nmap",
            "kali linux", "snort", "suricata", "yara",
        ],
        "soft": [
            "analytical", "attention to detail", "problem solving",
            "communication", "continuous learning",
        ],
        "metrics": [
            "mttd", "mttr", "false positive rate", "vulnerability count",
            "patch compliance", "incident count",
        ],
    },
}


# Mapping of industry keys to human-readable names
INDUSTRY_NAMES = {
    "software_engineering": "Software Engineering",
    "data_science": "Data Science / ML / AI",
    "data_engineering": "Data Engineering",
    "devops_sre": "DevOps / SRE / Cloud",
    "product_management": "Product Management",
    "design_ux": "Design / UX / UI",
    "marketing": "Marketing / Growth",
    "sales": "Sales / Business Development",
    "finance": "Finance / Accounting",
    "healthcare": "Healthcare / Medical",
    "education": "Education / Teaching",
    "human_resources": "Human Resources / Recruiting",
    "cybersecurity": "Cybersecurity / InfoSec",
}


# Industry-specific ATS tips
INDUSTRY_TIPS: dict[str, list[str]] = {
    "software_engineering": [
        "Lead with technical skills section (76% of tech recruiters search by skills first)",
        "Include specific tech versions (e.g., 'Python 3.11', 'React 18') for senior roles",
        "Quantify impact: API throughput, latency reductions, code coverage percentages",
        "Mention CI/CD, testing frameworks, and code quality tools explicitly",
        "Add GitHub profile and link to notable projects/contributions",
    ],
    "data_science": [
        "Highlight modeling techniques used (regression, classification, NLP, deep learning)",
        "Include model accuracy/performance metrics (F1, AUC, RMSE) in bullet points",
        "Mention data volume processed (e.g., '500GB datasets', '10M+ records')",
        "Add Kaggle profile, research papers, or notable analyses",
        "List both ML frameworks (PyTorch, TensorFlow) AND business tools (SQL, Tableau)",
    ],
    "devops_sre": [
        "Emphasize uptime/SLA achievements (e.g., '99.99% uptime')",
        "Include infrastructure scale (servers managed, requests/sec, cost savings)",
        "List specific CI/CD pipelines built and deployment frequency improvements",
        "Mention incident response metrics (MTTR reductions, on-call experience)",
        "Add certifications (AWS, Azure, GCP, CKA) prominently",
    ],
    "product_management": [
        "Lead with measurable business impact (revenue, growth, retention)",
        "Use PM frameworks language (jobs-to-be-done, OKRs, north star metrics)",
        "Show end-to-end ownership of product launches with metrics",
        "Demonstrate cross-functional leadership (engineering, design, marketing)",
        "Include user research/data insights that drove product decisions",
    ],
    "marketing": [
        "Lead with quantified campaign results (ROAS, conversion lifts, lead growth)",
        "Mention specific marketing automation/CRM tools by name",
        "Show experience with both organic (SEO, content) AND paid channels",
        "Include funnel metrics (MQL, SQL, CAC, LTV)",
        "Add portfolio links for content/campaign examples",
    ],
    "sales": [
        "Lead EVERY bullet with quota attainment % or revenue numbers",
        "Include deal sizes, sales cycle length, and pipeline values",
        "Mention specific sales methodologies (Challenger, MEDDIC, SPIN)",
        "Show progression in territory size/quota over time",
        "Quantify customer retention and expansion revenue",
    ],
    "finance": [
        "Quantify deal sizes, transaction values, portfolio AUM",
        "Mention specific financial models built (DCF, LBO, M&A models)",
        "Include CFA, CPA, MBA, or relevant certifications prominently",
        "Highlight regulatory expertise (GAAP, IFRS, Dodd-Frank, SOX)",
        "Show technical proficiency (Excel modeling, SQL, Python for finance)",
    ],
    "healthcare": [
        "Lead with patient population size and care setting",
        "Mention specific EHR systems used (Epic, Cerner, Meditech)",
        "Include outcome metrics (readmission, satisfaction, compliance)",
        "Add all licenses and certifications with expiration dates",
        "Highlight quality improvement initiatives with measurable outcomes",
    ],
    "education": [
        "Mention grade levels, subjects, and student population size",
        "Include test score improvements or learning outcome data",
        "Highlight technology integration (LMS platforms, EdTech tools)",
        "Add curriculum development experience with measurable impact",
        "Include all teaching certifications and ongoing PD",
    ],
    "human_resources": [
        "Quantify recruiting metrics (time-to-fill, quality-of-hire, diversity %)",
        "Mention specific ATS/HRIS platforms used",
        "Include scope of program management (# employees impacted)",
        "Highlight DEI initiatives with measurable outcomes",
        "Show compliance/legal knowledge (FLSA, FMLA, ADA, EEOC)",
    ],
    "cybersecurity": [
        "Include all security certifications (CISSP, CEH, OSCP, Security+)",
        "Quantify threats prevented, vulnerabilities remediated, MTTR reductions",
        "Mention specific security tools and SIEM platforms by name",
        "Highlight incident response leadership and post-mortem authorship",
        "Include compliance framework experience (SOC 2, ISO 27001, HIPAA, PCI)",
    ],
    "data_engineering": [
        "Quantify data volume (TB, PB) and pipeline throughput",
        "Mention specific data stack components (warehouse, lake, orchestrator)",
        "Highlight cost optimization with dollar amounts saved",
        "Include data quality/governance initiatives",
        "Show experience with both batch AND streaming data",
    ],
    "design_ux": [
        "Always include a portfolio link prominently",
        "Mention specific design systems built or contributed to",
        "Quantify usability improvements (task completion, error rates)",
        "Include user research methods used (interviews, surveys, A/B tests)",
        "Highlight accessibility (WCAG) compliance work",
    ],
}


@dataclass
class IndustryAnalysis:
    """Result of industry detection on a job description."""
    primary_industry: str = ""
    primary_industry_name: str = ""
    confidence: float = 0.0
    secondary_industries: list[tuple[str, float]] = field(default_factory=list)
    industry_keywords_in_jd: list[str] = field(default_factory=list)
    industry_keywords_missing: list[str] = field(default_factory=list)
    industry_tips: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_industry": self.primary_industry,
            "primary_industry_name": self.primary_industry_name,
            "confidence": round(self.confidence, 1),
            "secondary_industries": [
                {"key": k, "name": INDUSTRY_NAMES.get(k, k), "score": round(s, 1)}
                for k, s in self.secondary_industries
            ],
            "industry_keywords_in_jd": self.industry_keywords_in_jd,
            "industry_keywords_missing": self.industry_keywords_missing,
            "industry_tips": self.industry_tips,
        }


def detect_industry(job_description: str) -> IndustryAnalysis:
    """Detect the most likely industry/domain of a job description.

    Uses keyword frequency matching against curated industry banks.

    Args:
        job_description: The full JD text.

    Returns:
        IndustryAnalysis with primary industry, confidence, and tips.
    """
    text_lower = job_description.lower()
    scores: dict[str, float] = {}
    matched_keywords: dict[str, list[str]] = {}

    for industry, categories in INDUSTRY_KEYWORDS.items():
        all_kws = []
        for cat_kws in categories.values():
            all_kws.extend(cat_kws)

        matches = []
        for kw in all_kws:
            # Word-boundary aware search for short keywords
            if len(kw) <= 4:
                if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                    matches.append(kw)
            elif kw in text_lower:
                matches.append(kw)

        # Score = weighted by category (core matters more than tools)
        core_matches = sum(1 for k in matches if k in categories.get("core", []))
        tools_matches = sum(1 for k in matches if k in categories.get("tools", []))
        soft_matches = sum(1 for k in matches if k in categories.get("soft", []))
        metrics_matches = sum(1 for k in matches if k in categories.get("metrics", []))

        score = (core_matches * 3.0 + tools_matches * 1.5 + soft_matches * 1.0 + metrics_matches * 1.5)
        scores[industry] = score
        matched_keywords[industry] = matches

    if not scores or max(scores.values()) == 0:
        return IndustryAnalysis(
            primary_industry="general",
            primary_industry_name="General / Unknown",
            confidence=0.0,
        )

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_industry, top_score = ranked[0]
    total_score = sum(scores.values())
    confidence = (top_score / total_score) * 100 if total_score > 0 else 0

    # Get secondary industries (>20% of top score)
    secondary = [
        (ind, sc) for ind, sc in ranked[1:6]
        if sc > 0 and sc >= top_score * 0.2
    ]

    # Find what's in JD vs what's missing for this industry
    industry_kws = []
    for cat_kws in INDUSTRY_KEYWORDS[top_industry].values():
        industry_kws.extend(cat_kws)
    in_jd = sorted(set(matched_keywords[top_industry]))
    missing = sorted(set(industry_kws) - set(in_jd))

    return IndustryAnalysis(
        primary_industry=top_industry,
        primary_industry_name=INDUSTRY_NAMES.get(top_industry, top_industry),
        confidence=confidence,
        secondary_industries=secondary,
        industry_keywords_in_jd=in_jd[:30],
        industry_keywords_missing=missing[:30],
        industry_tips=INDUSTRY_TIPS.get(top_industry, []),
    )


def get_industry_keywords(industry_key: str, category: str = "all") -> list[str]:
    """Get keywords for a specific industry and category.

    Args:
        industry_key: One of the keys in INDUSTRY_KEYWORDS.
        category: 'core', 'tools', 'soft', 'metrics', or 'all'.

    Returns:
        List of keywords.
    """
    if industry_key not in INDUSTRY_KEYWORDS:
        return []
    categories = INDUSTRY_KEYWORDS[industry_key]
    if category == "all":
        result = []
        for cat_kws in categories.values():
            result.extend(cat_kws)
        return sorted(set(result))
    return sorted(set(categories.get(category, [])))


def list_industries() -> list[dict[str, str]]:
    """List all supported industries with their human-readable names."""
    return [{"key": k, "name": v} for k, v in INDUSTRY_NAMES.items()]

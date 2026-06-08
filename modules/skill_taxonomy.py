"""
CV Tailor — Skill Taxonomy & Categorization
============================================
Auto-categorizes skills into standard groups (Languages, Frameworks, Cloud,
Databases, Tools, Methodologies, Soft Skills) for clean Skills section formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Skill Categories (canonical lowercase keys)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SKILL_CATEGORIES: dict[str, set[str]] = {
    "Programming Languages": {
        "python", "java", "javascript", "typescript", "c", "c++", "c#",
        "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "scala",
        "r", "matlab", "perl", "bash", "shell", "powershell", "dart",
        "objective-c", "lua", "haskell", "clojure", "elixir", "erlang",
        "f#", "vb.net", "vba", "groovy", "julia", "solidity", "assembly",
        "fortran", "cobol", "sql", "pl/sql", "t-sql",
    },
    "Web Frameworks & Libraries": {
        "react", "angular", "vue", "vue.js", "svelte", "next.js", "nuxt.js",
        "gatsby", "remix", "astro", "ember", "backbone", "jquery",
        "node.js", "express", "express.js", "fastify", "nestjs", "koa",
        "django", "flask", "fastapi", "pyramid", "tornado", "bottle",
        "spring", "spring boot", "struts", "play", "vert.x",
        "rails", "ruby on rails", "sinatra",
        "laravel", "symfony", "codeigniter", "yii", "zend",
        "asp.net", ".net", "blazor", "asp.net core",
        "html", "html5", "css", "css3", "sass", "scss", "less", "tailwind",
        "tailwind css", "bootstrap", "material-ui", "mui", "chakra ui",
        "ant design", "styled-components", "emotion",
        "webpack", "vite", "rollup", "parcel", "esbuild", "turbopack",
        "redux", "mobx", "zustand", "vuex", "pinia", "rxjs",
    },
    "Data & ML Frameworks": {
        "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
        "xgboost", "lightgbm", "catboost", "statsmodels", "nltk", "spacy",
        "hugging face", "transformers", "langchain", "llamaindex",
        "mlflow", "kubeflow", "ray", "dask", "polars", "pyspark", "spark",
        "opencv", "fastai", "jax", "onnx", "tensorrt", "openai",
        "anthropic", "cohere", "llama", "gpt", "bert", "stable diffusion",
    },
    "Databases": {
        "postgresql", "postgres", "mysql", "mariadb", "sqlite", "oracle",
        "sql server", "mssql", "db2",
        "mongodb", "cassandra", "couchbase", "couchdb", "dynamodb",
        "redis", "memcached", "elasticsearch", "opensearch", "solr",
        "neo4j", "arangodb", "orientdb",
        "snowflake", "bigquery", "redshift", "databricks", "synapse",
        "clickhouse", "vertica", "teradata", "presto", "trino",
        "influxdb", "timescaledb", "questdb", "victoriametrics",
        "pinecone", "weaviate", "qdrant", "milvus", "chroma", "faiss",
        "firebase", "firestore", "supabase", "planetscale",
    },
    "Cloud & DevOps": {
        "aws", "amazon web services", "azure", "gcp", "google cloud",
        "ibm cloud", "oracle cloud", "alibaba cloud", "digitalocean",
        "heroku", "vercel", "netlify", "cloudflare", "fastly",
        "docker", "kubernetes", "k8s", "openshift", "rancher", "nomad",
        "helm", "kustomize", "istio", "linkerd", "envoy",
        "terraform", "pulumi", "ansible", "puppet", "chef", "salt",
        "cloudformation", "arm templates", "bicep",
        "jenkins", "github actions", "gitlab ci", "circleci", "travis ci",
        "bitbucket pipelines", "argocd", "spinnaker", "tekton", "drone",
        "prometheus", "grafana", "datadog", "new relic", "splunk",
        "elk", "elastic stack", "logstash", "kibana", "fluentd", "loki",
        "jaeger", "zipkin", "opentelemetry", "sentry", "rollbar",
        "lambda", "ec2", "s3", "rds", "ecs", "eks", "fargate", "sqs", "sns",
        "azure functions", "app service", "aks", "cloud functions",
        "cloud run", "gke", "vertex ai", "sagemaker",
    },
    "Tools & Platforms": {
        "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
        "jira", "confluence", "trello", "asana", "monday", "linear",
        "notion", "slack", "microsoft teams", "discord", "zoom",
        "figma", "sketch", "adobe xd", "invision", "miro", "lucidchart",
        "postman", "insomnia", "swagger", "openapi", "stoplight",
        "vs code", "intellij", "pycharm", "webstorm", "eclipse",
        "visual studio", "sublime text", "vim", "emacs", "neovim",
        "linux", "ubuntu", "centos", "rhel", "debian", "windows", "macos",
        "tableau", "power bi", "looker", "qlik", "metabase", "superset",
        "salesforce", "hubspot", "marketo", "pardot", "mailchimp",
        "sap", "oracle erp", "workday", "netsuite", "quickbooks",
        "stripe", "paypal", "square", "shopify", "magento", "woocommerce",
    },
    "Methodologies & Practices": {
        "agile", "scrum", "kanban", "lean", "safe", "waterfall", "xp",
        "ci/cd", "continuous integration", "continuous deployment",
        "tdd", "test driven development", "bdd", "behavior driven development",
        "ddd", "domain driven design", "microservices", "monolith",
        "rest", "restful", "graphql", "grpc", "soap", "websockets",
        "oauth", "oidc", "saml", "jwt", "sso",
        "devops", "devsecops", "gitops", "sre", "site reliability",
        "design patterns", "solid", "dry", "kiss", "yagni",
        "mvc", "mvp", "mvvm", "clean architecture", "hexagonal architecture",
        "event-driven", "event sourcing", "cqrs", "saga pattern",
        "data modeling", "data warehousing", "etl", "elt",
        "machine learning", "deep learning", "nlp", "computer vision",
        "reinforcement learning", "supervised learning", "unsupervised learning",
        "a/b testing", "user research", "usability testing", "wireframing",
        "prototyping", "design thinking", "design systems",
    },
    "Testing & QA": {
        "pytest", "unittest", "nose", "mock", "tox",
        "jest", "mocha", "chai", "jasmine", "karma", "ava", "vitest",
        "junit", "testng", "mockito", "easymock",
        "rspec", "minitest", "cucumber", "gherkin",
        "selenium", "cypress", "playwright", "puppeteer", "webdriver",
        "appium", "espresso", "xcuitest", "detox",
        "postman", "soapui", "rest assured", "karate", "k6",
        "jmeter", "gatling", "locust", "loadrunner",
        "sonarqube", "coverity", "veracode", "snyk", "checkmarx",
        "test automation", "manual testing", "regression testing",
        "performance testing", "load testing", "stress testing",
        "security testing", "penetration testing",
    },
    "Security": {
        "cybersecurity", "information security", "infosec", "appsec", "netsec",
        "owasp", "sast", "dast", "iast", "rasp", "siem", "soar", "edr", "xdr",
        "penetration testing", "pen testing", "ethical hacking",
        "vulnerability assessment", "threat modeling", "threat hunting",
        "incident response", "forensics", "malware analysis",
        "cryptography", "encryption", "pki", "tls", "ssl",
        "iam", "identity management", "zero trust", "least privilege",
        "firewall", "ids", "ips", "waf", "vpn", "dlp",
        "cissp", "ceh", "oscp", "security+", "cisa", "cism",
        "iso 27001", "soc 2", "pci dss", "hipaa", "gdpr", "nist", "fedramp",
        "splunk", "qradar", "crowdstrike", "sentinelone", "carbon black",
        "wireshark", "metasploit", "burp suite", "nessus", "nmap",
        "kali linux", "snort", "suricata",
    },
    "Soft Skills": {
        "leadership", "communication", "teamwork", "collaboration",
        "problem solving", "critical thinking", "analytical thinking",
        "creativity", "innovation", "adaptability", "flexibility",
        "time management", "organization", "prioritization", "multitasking",
        "attention to detail", "decision making", "strategic thinking",
        "project management", "stakeholder management", "people management",
        "mentoring", "coaching", "training",
        "presentation", "public speaking", "writing", "storytelling",
        "negotiation", "conflict resolution", "active listening", "empathy",
        "emotional intelligence", "eq", "cultural awareness",
        "customer service", "customer focus", "customer obsession",
        "ownership", "accountability", "initiative", "self-motivated",
        "results-oriented", "data-driven", "detail-oriented",
        "cross-functional", "interdisciplinary", "remote work", "agile mindset",
    },
    "Certifications": {
        "aws certified", "azure certified", "gcp certified", "google cloud certified",
        "aws solutions architect", "aws developer", "aws sysops",
        "azure administrator", "azure developer", "azure solutions architect",
        "cka", "ckad", "cks", "certified kubernetes administrator",
        "cissp", "ceh", "oscp", "security+", "network+", "cisa", "cism",
        "pmp", "prince2", "csm", "psm", "pmi-acp", "safe agilist",
        "itil", "cobit", "togaf",
        "cfa", "cpa", "cma", "frm", "caia",
        "phr", "sphr", "shrm-cp", "shrm-scp",
        "six sigma", "lean six sigma", "green belt", "black belt",
        "scrum master", "product owner", "kanban",
        "comptia", "ccna", "ccnp", "ccie",
    },
    "Languages (Spoken)": {
        "english", "spanish", "french", "german", "italian", "portuguese",
        "mandarin", "cantonese", "japanese", "korean", "arabic", "hebrew",
        "russian", "polish", "dutch", "swedish", "norwegian", "danish",
        "finnish", "greek", "turkish", "hindi", "urdu", "bengali", "tamil",
        "telugu", "punjabi", "vietnamese", "thai", "indonesian", "malay",
        "filipino", "tagalog", "swahili", "afrikaans",
    },
}


@dataclass
class CategorizedSkills:
    """Result of skill categorization."""
    categorized: dict[str, list[str]] = field(default_factory=dict)
    uncategorized: list[str] = field(default_factory=list)
    total_skills: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "categorized": self.categorized,
            "uncategorized": self.uncategorized,
            "total_skills": self.total_skills,
            "category_count": len(self.categorized),
        }

    def format_as_resume_section(self, separator: str = " | ") -> str:
        """Format as a clean Skills section for the resume.

        Example output:
            Programming Languages: Python, Java, JavaScript
            Cloud & DevOps: AWS, Docker, Kubernetes
            ...
        """
        lines = []
        for category, skills in self.categorized.items():
            if skills:
                lines.append(f"{category}: {', '.join(skills)}")
        if self.uncategorized:
            lines.append(f"Other: {', '.join(self.uncategorized)}")
        return "\n".join(lines)

    def format_compact(self) -> str:
        """One-line compact format with pipe separators."""
        parts = []
        for category, skills in self.categorized.items():
            if skills:
                parts.append(f"{category}: {', '.join(skills)}")
        return " | ".join(parts)


def categorize_skills(skills: list[str]) -> CategorizedSkills:
    """Group a flat list of skills into standard categories.

    Args:
        skills: Flat list of skill strings (can be mixed case).

    Returns:
        CategorizedSkills with skills grouped by category, preserving
        original casing. Categories with no skills are omitted.
    """
    result: dict[str, list[str]] = {cat: [] for cat in SKILL_CATEGORIES}
    uncategorized: list[str] = []
    seen: set[str] = set()

    for skill in skills:
        if not skill or not isinstance(skill, str):
            continue
        skill_clean = skill.strip()
        if not skill_clean:
            continue
        skill_lower = skill_clean.lower()
        if skill_lower in seen:
            continue
        seen.add(skill_lower)

        matched = False
        for category, kw_set in SKILL_CATEGORIES.items():
            if skill_lower in kw_set:
                result[category].append(skill_clean)
                matched = True
                break

        if not matched:
            # Try partial / substring match for compound skills like "Python 3.11"
            for category, kw_set in SKILL_CATEGORIES.items():
                for kw in kw_set:
                    if len(kw) >= 4 and (kw in skill_lower or skill_lower in kw):
                        result[category].append(skill_clean)
                        matched = True
                        break
                if matched:
                    break

        if not matched:
            uncategorized.append(skill_clean)

    # Sort each category alphabetically and remove empties
    final = {}
    for cat, items in result.items():
        if items:
            final[cat] = sorted(items, key=str.lower)

    return CategorizedSkills(
        categorized=final,
        uncategorized=sorted(uncategorized, key=str.lower),
        total_skills=len(seen),
    )


def get_category_for_skill(skill: str) -> str:
    """Return the category name for a single skill, or 'Uncategorized'."""
    skill_lower = skill.strip().lower()
    for category, kw_set in SKILL_CATEGORIES.items():
        if skill_lower in kw_set:
            return category
    for category, kw_set in SKILL_CATEGORIES.items():
        for kw in kw_set:
            if len(kw) >= 4 and (kw in skill_lower or skill_lower in kw):
                return category
    return "Uncategorized"


def list_categories() -> list[str]:
    """Return the names of all skill categories."""
    return list(SKILL_CATEGORIES.keys())

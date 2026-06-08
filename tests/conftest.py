"""Shared test fixtures for the CV Maker test suite."""

import pytest


@pytest.fixture
def sample_resume_data():
    """Return a sample resume as a structured dict (matches ResumeData schema)."""
    return {
        "name": "Jane Doe",
        "email": "jane.doe@email.com",
        "phone": "+1-555-0100",
        "linkedin": "linkedin.com/in/janedoe",
        "summary": (
            "Senior software engineer with 8 years of experience in Python, "
            "cloud architecture, and team leadership. Proven track record of "
            "delivering scalable microservices and mentoring junior developers."
        ),
        "skills": [
            "Python", "JavaScript", "TypeScript", "AWS", "Docker", "Kubernetes",
            "PostgreSQL", "Redis", "REST APIs", "CI/CD", "Agile", "Git",
        ],
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "start_date": "2020-01",
                "end_date": "Present",
                "bullets": [
                    "Led migration of monolithic application to microservices, reducing deployment time by 60%",
                    "Managed team of 15 engineers across 3 time zones",
                    "Implemented CI/CD pipeline that increased release frequency by 200%",
                    "Reduced cloud infrastructure costs by $150K annually through optimization",
                ],
            },
            {
                "title": "Software Engineer",
                "company": "StartupXYZ",
                "start_date": "2016-06",
                "end_date": "2019-12",
                "bullets": [
                    "Built RESTful APIs serving 10 million requests per day",
                    "Designed and implemented real-time notification system using WebSockets",
                    "Improved database query performance by 45% through indexing and optimization",
                ],
            },
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "State University",
                "year": "2016",
            }
        ],
        "projects": [
            {
                "name": "Open Source CLI Tool",
                "description": "A command-line tool for automating cloud deployments with 500+ GitHub stars",
            }
        ],
    }


@pytest.fixture
def sample_resume_text():
    """Return a sample resume as plain text (used by ATS optimizer, tailor, etc.)."""
    return """Jane Doe
jane.doe@email.com | +1-555-0100 | linkedin.com/in/janedoe

Summary
Senior software engineer with 8 years of experience in Python, cloud architecture, and team leadership. Proven track record of delivering scalable microservices and mentoring junior developers.

Skills
Python, JavaScript, TypeScript, AWS, Docker, Kubernetes, PostgreSQL, Redis, REST APIs, CI/CD, Agile, Git

Experience
Senior Software Engineer | Tech Corp | 2020-01 - Present
- Led migration of monolithic application to microservices, reducing deployment time by 60%
- Managed team of 15 engineers across 3 time zones
- Implemented CI/CD pipeline that increased release frequency by 200%
- Reduced cloud infrastructure costs by $150K annually through optimization

Software Engineer | StartupXYZ | 2016-06 - 2019-12
- Built RESTful APIs serving 10 million requests per day
- Designed and implemented real-time notification system using WebSockets
- Improved database query performance by 45% through indexing and optimization

Education
B.S. Computer Science | State University | 2016

Projects
Open Source CLI Tool - A command-line tool for automating cloud deployments with 500+ GitHub stars
"""


@pytest.fixture
def sample_job_description():
    """Return a sample job description for tailoring / analysis tests."""
    return """Senior Python Developer - Cloud Platform

We are looking for a Senior Python Developer to join our cloud platform team.

Requirements:
- 5+ years of experience with Python
- Strong experience with AWS services (EC2, S3, Lambda, ECS)
- Experience with containerization (Docker, Kubernetes)
- Proficiency in building RESTful APIs and microservices
- Experience with PostgreSQL and Redis
- Familiarity with CI/CD pipelines and DevOps practices
- Strong problem-solving and communication skills
- Experience with Agile methodologies

Nice to have:
- Experience with Terraform or CloudFormation
- Knowledge of machine learning frameworks
- Open source contributions

Responsibilities:
- Design and implement scalable cloud-native applications
- Lead code reviews and mentor junior developers
- Collaborate with cross-functional teams to define technical requirements
- Optimize application performance and reliability
- Contribute to architectural decisions and technical roadmap
"""

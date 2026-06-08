#!/usr/bin/env python3
"""
CV Tailor — Main CLI Entry Point
===================================
A production-ready ATS-friendly CV maker and tailoring system.

Usage examples:
    python main.py build --json sample_data/sample_resume.json --format pdf
    python main.py build --json sample_data/sample_resume.json --format docx --template modern
    python main.py tailor --resume resume.txt --jd job.txt
    python main.py ats --resume resume.txt --jd job.txt
    python main.py analyze-jd --jd job.txt
    python main.py voice --output resume_from_voice.txt
    python main.py cover-letter --resume resume.txt --jd job.txt --company "Acme"
    python main.py linkedin --resume resume.txt
    python main.py translate --resume resume.txt --language Spanish
    python main.py interactive
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_settings, OUTPUTS_DIR
from utils.logging_config import setup_logging


def _read_text_file(path: str) -> str:
    """Read a text file and return its contents."""
    p = Path(path)
    if not p.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Command handlers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def cmd_build(args: argparse.Namespace) -> None:
    """Build a resume from JSON data."""
    from modules.resume_builder import ResumeBuilder
    from modules.templates import export_pdf_template, export_docx_template

    builder = ResumeBuilder()

    if args.json:
        builder.load_json(args.json)
    else:
        print("❌ Please provide --json with resume data.")
        sys.exit(1)

    # AI enhancement
    if args.enhance:
        print("🧠 Enhancing resume with AI…")
        builder.enhance_with_ai()
        print("✅ Enhancement complete.")

    # Export
    template = args.template or "professional"
    fmt = args.format or "pdf"

    data = builder.get_data()
    if fmt == "pdf":
        path = export_pdf_template(data, template_name=template, output_path=args.output)
    elif fmt == "docx":
        path = export_docx_template(data, template_name=template, output_path=args.output)
    elif fmt == "txt":
        path = builder.export("txt", output_path=args.output)
    else:
        print(f"❌ Unknown format: {fmt}")
        sys.exit(1)

    print(f"✅ Resume exported: {path}")


def cmd_tailor(args: argparse.Namespace) -> None:
    """Tailor a resume to a job description."""
    from modules.resume_tailor import ResumeTailor

    resume_text = _read_text_file(args.resume)
    jd_text = _read_text_file(args.jd)

    tailor = ResumeTailor()
    print("🔄 Tailoring resume to job description…")
    result = tailor.tailor(resume_text, jd_text, use_ai=not args.no_ai)

    # Print report
    report = result["keyword_report"]
    print(f"\n📊 Original Keyword Match: {report['match_rate']}%")
    print(f"   Matched: {', '.join(report['matched'][:10])}")
    print(f"   Missing: {', '.join(report['missing'][:10])}")

    tailored_report = result.get("tailored_keyword_report", {})
    if tailored_report:
        print(f"\n📊 After Tailoring: {tailored_report.get('match_rate', 0)}%")

    if result.get("ats_keywords_added"):
        print(f"   Keywords added: {', '.join(result['ats_keywords_added'][:10])}")

    print("\n💡 Suggestions:")
    for s in result.get("suggestions", []):
        print(f"   {s}")

    # Save tailored resume
    output_path = args.output or str(OUTPUTS_DIR / "tailored_resume.txt")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(result["tailored_resume"], encoding="utf-8")
    print(f"\n✅ Tailored resume saved: {output_path}")


def cmd_ats(args: argparse.Namespace) -> None:
    """Run ATS compatibility analysis."""
    from modules.ats_optimizer import ATSOptimizer

    resume_text = _read_text_file(args.resume)
    jd_text = _read_text_file(args.jd) if args.jd else None

    optimizer = ATSOptimizer()
    print("🔍 Running ATS analysis…")
    report = optimizer.analyse(resume_text, jd_text)
    print(report.summary_text())


def cmd_analyze_jd(args: argparse.Namespace) -> None:
    """Analyse a job description."""
    from modules.job_analyzer import JobAnalyzer

    jd_text = _read_text_file(args.jd)
    resume_text = _read_text_file(args.resume) if args.resume else None

    analyzer = JobAnalyzer()

    if resume_text:
        print("🔍 Comparing job description against resume…")
        analysis = analyzer.compare(jd_text, resume_text, use_ai=not args.no_ai)
    else:
        print("🔍 Analysing job description…")
        analysis = analyzer.analyse(jd_text, use_ai=not args.no_ai)

    print(analysis.summary_text())


def cmd_voice(args: argparse.Namespace) -> None:
    """Record voice input and generate structured resume text."""
    from modules.voice_input import VoiceInput

    voice = VoiceInput()

    if args.list_devices:
        devices = voice.list_audio_devices()
        print("\n🎤 Available Audio Input Devices:")
        for d in devices:
            print(f"   [{d.get('index', '?')}] {d.get('name', 'Unknown')} "
                  f"(channels: {d.get('channels', '?')}, rate: {d.get('sample_rate', '?')})")
        return

    audio_path = args.audio if args.audio else None
    structured = voice.voice_to_resume(audio_path)

    output_path = args.output or str(OUTPUTS_DIR / "voice_resume.txt")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(structured, encoding="utf-8")
    print(f"\n✅ Structured resume saved: {output_path}")
    print("\n--- Preview ---")
    print(structured[:500])
    if len(structured) > 500:
        print("… [truncated]")


def cmd_cover_letter(args: argparse.Namespace) -> None:
    """Generate a cover letter."""
    from modules.bonus_features import CoverLetterGenerator

    resume_text = _read_text_file(args.resume)
    jd_text = _read_text_file(args.jd)

    gen = CoverLetterGenerator()
    print("📝 Generating cover letter…")
    letter = gen.generate(
        resume_text=resume_text,
        job_description=jd_text,
        company_name=args.company or "",
        hiring_manager=args.manager or "",
    )

    output_path = args.output or str(OUTPUTS_DIR / "cover_letter.txt")
    gen.save(letter, output_path)
    print(f"✅ Cover letter saved: {output_path}")
    print(f"\n--- Preview ---\n{letter[:400]}…")


def cmd_linkedin(args: argparse.Namespace) -> None:
    """Generate a LinkedIn summary."""
    from modules.bonus_features import LinkedInSummaryGenerator

    resume_text = _read_text_file(args.resume)

    gen = LinkedInSummaryGenerator()
    print("🔗 Generating LinkedIn summary…")
    summary = gen.generate(resume_text)

    output_path = args.output or str(OUTPUTS_DIR / "linkedin_summary.txt")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(summary, encoding="utf-8")
    print(f"✅ LinkedIn summary saved: {output_path}")
    print(f"\n{summary}")


def cmd_translate(args: argparse.Namespace) -> None:
    """Translate a resume to another language."""
    from modules.bonus_features import MultilingualResume

    if args.list_languages:
        print("🌐 Supported Languages:")
        for lang in MultilingualResume.list_languages():
            print(f"   • {lang}")
        return

    resume_text = _read_text_file(args.resume)
    language = args.language

    ml = MultilingualResume()
    print(f"🌐 Translating resume to {language}…")
    translated = ml.translate(resume_text, language)

    output_path = args.output or str(OUTPUTS_DIR / f"resume_{language.lower()}.txt")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(translated, encoding="utf-8")
    print(f"✅ Translated resume saved: {output_path}")
    print(f"\n--- Preview ---\n{translated[:400]}…")


def cmd_interactive(args: argparse.Namespace) -> None:
    """Interactive CLI mode — guided resume building."""
    from modules.resume_builder import ResumeBuilder
    from modules.templates import export_pdf_template, list_templates

    print("\n" + "═" * 50)
    print("  CV TAILOR — Interactive Resume Builder")
    print("═" * 50 + "\n")

    builder = ResumeBuilder()

    # Contact info
    name = input("📝 Full name: ").strip()
    email = input("📧 Email: ").strip()
    phone = input("📱 Phone: ").strip()
    location = input("📍 Location (City, State): ").strip()
    linkedin = input("🔗 LinkedIn URL (optional): ").strip()
    website = input("🌐 Website (optional): ").strip()

    builder.set_contact(name, email, phone, location, linkedin, website)

    # Summary
    print("\n📝 Professional Summary (press Enter twice to finish):")
    summary_lines = []
    while True:
        line = input()
        if line == "":
            break
        summary_lines.append(line)
    builder.set_summary(" ".join(summary_lines))

    # Skills
    skills_input = input("\n🛠️  Skills (comma-separated): ").strip()
    if skills_input:
        builder.set_skills([s.strip() for s in skills_input.split(",") if s.strip()])

    # Experience
    print("\n💼 Work Experience (type 'done' when finished):")
    while True:
        title = input("   Job title (or 'done'): ").strip()
        if title.lower() == "done":
            break
        company = input("   Company: ").strip()
        loc = input("   Location: ").strip()
        start = input("   Start date: ").strip()
        end = input("   End date (or 'Present'): ").strip() or "Present"
        print("   Bullet points (one per line, empty line to finish):")
        bullets = []
        while True:
            b = input("     • ").strip()
            if not b:
                break
            bullets.append(b)
        builder.add_experience(title, company, loc, start, end, bullets)
        print()

    # Education
    print("\n🎓 Education (type 'done' when finished):")
    while True:
        degree = input("   Degree (or 'done'): ").strip()
        if degree.lower() == "done":
            break
        institution = input("   Institution: ").strip()
        loc = input("   Location: ").strip()
        grad_date = input("   Graduation date: ").strip()
        gpa = input("   GPA (optional): ").strip()
        builder.add_education(degree, institution, loc, grad_date, gpa)
        print()

    # Certifications
    certs_input = input("\n📜 Certifications (comma-separated, or Enter to skip): ").strip()
    if certs_input:
        for cert in certs_input.split(","):
            builder.add_certification(cert.strip())

    # Languages
    langs_input = input("\n🌐 Languages (comma-separated, or Enter to skip): ").strip()
    if langs_input:
        builder.set_languages([l.strip() for l in langs_input.split(",") if l.strip()])

    # AI Enhancement
    enhance = input("\n🧠 Enhance with AI? (y/N): ").strip().lower()
    if enhance == "y":
        try:
            builder.enhance_with_ai()
            print("✅ AI enhancement applied!")
        except Exception as e:
            print(f"⚠️  AI enhancement failed: {e}")

    # Template selection
    print("\n🎨 Available templates:")
    for t in list_templates():
        print(f"   • {t['name']}: {t['description']}")
    template = input("   Choose template (minimal/professional/modern) [professional]: ").strip() or "professional"

    # Format
    fmt = input("📄 Export format (pdf/docx) [pdf]: ").strip() or "pdf"

    # Export
    data = builder.get_data()
    if fmt == "pdf":
        path = export_pdf_template(data, template_name=template)
    else:
        from modules.templates import export_docx_template
        path = export_docx_template(data, template_name=template)

    print(f"\n✅ Resume exported: {path}")

    # Save JSON for future use
    json_path = OUTPUTS_DIR / f"{name.replace(' ', '_').lower()}_data.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"💾 Resume data saved: {json_path}")

    print("\n🎉 Done! Your ATS-friendly resume is ready.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Argument parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cv_tailor",
        description="CV Tailor — ATS-friendly CV Maker & Tailoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py build --json sample_data/sample_resume.json --format pdf\n"
            "  python main.py build --json sample_data/sample_resume.json --template modern --enhance\n"
            "  python main.py tailor --resume resume.txt --jd job.txt\n"
            "  python main.py ats --resume resume.txt\n"
            "  python main.py ats --resume resume.txt --jd job.txt\n"
            "  python main.py analyze-jd --jd job.txt --resume resume.txt\n"
            "  python main.py cover-letter --resume resume.txt --jd job.txt --company Acme\n"
            "  python main.py linkedin --resume resume.txt\n"
            "  python main.py translate --resume resume.txt --language Spanish\n"
            "  python main.py voice --audio recording.wav\n"
            "  python main.py interactive\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── build ──
    p_build = subparsers.add_parser("build", help="Build a resume from JSON data")
    p_build.add_argument("--json", required=True, help="Path to resume data JSON file")
    p_build.add_argument("--format", choices=["pdf", "docx", "txt"], default="pdf", help="Output format")
    p_build.add_argument("--template", choices=["minimal", "professional", "modern"], default="professional")
    p_build.add_argument("--output", help="Custom output file path")
    p_build.add_argument("--enhance", action="store_true", help="Enhance with AI (requires API key)")
    p_build.set_defaults(func=cmd_build)

    # ── tailor ──
    p_tailor = subparsers.add_parser("tailor", help="Tailor a resume to a job description")
    p_tailor.add_argument("--resume", required=True, help="Path to resume text file")
    p_tailor.add_argument("--jd", required=True, help="Path to job description text file")
    p_tailor.add_argument("--output", help="Output path for tailored resume")
    p_tailor.add_argument("--no-ai", action="store_true", help="Skip AI rewriting (basic mode)")
    p_tailor.set_defaults(func=cmd_tailor)

    # ── ats ──
    p_ats = subparsers.add_parser("ats", help="Run ATS compatibility analysis")
    p_ats.add_argument("--resume", required=True, help="Path to resume text file")
    p_ats.add_argument("--jd", help="Path to job description (optional, for keyword analysis)")
    p_ats.set_defaults(func=cmd_ats)

    # ── analyze-jd ──
    p_jd = subparsers.add_parser("analyze-jd", help="Analyse a job description")
    p_jd.add_argument("--jd", required=True, help="Path to job description text file")
    p_jd.add_argument("--resume", help="Path to resume (for comparison)")
    p_jd.add_argument("--no-ai", action="store_true", help="Skip AI extraction")
    p_jd.set_defaults(func=cmd_analyze_jd)

    # ── voice ──
    p_voice = subparsers.add_parser("voice", help="Voice-to-resume pipeline")
    p_voice.add_argument("--audio", help="Path to audio file (records from mic if omitted)")
    p_voice.add_argument("--output", help="Output path for structured resume text")
    p_voice.add_argument("--list-devices", action="store_true", help="List audio input devices")
    p_voice.set_defaults(func=cmd_voice)

    # ── cover-letter ──
    p_cl = subparsers.add_parser("cover-letter", help="Generate a cover letter")
    p_cl.add_argument("--resume", required=True, help="Path to resume text file")
    p_cl.add_argument("--jd", required=True, help="Path to job description")
    p_cl.add_argument("--company", help="Company name")
    p_cl.add_argument("--manager", help="Hiring manager name")
    p_cl.add_argument("--output", help="Output file path")
    p_cl.set_defaults(func=cmd_cover_letter)

    # ── linkedin ──
    p_li = subparsers.add_parser("linkedin", help="Generate LinkedIn summary")
    p_li.add_argument("--resume", required=True, help="Path to resume text file")
    p_li.add_argument("--output", help="Output file path")
    p_li.set_defaults(func=cmd_linkedin)

    # ── translate ──
    p_tr = subparsers.add_parser("translate", help="Translate resume to another language")
    p_tr.add_argument("--resume", help="Path to resume text file")
    p_tr.add_argument("--language", help="Target language (e.g., Spanish, French)")
    p_tr.add_argument("--output", help="Output file path")
    p_tr.add_argument("--list-languages", action="store_true", help="List supported languages")
    p_tr.set_defaults(func=cmd_translate)

    # ── interactive ──
    p_int = subparsers.add_parser("interactive", help="Interactive guided resume builder")
    p_int.set_defaults(func=cmd_interactive)

    return parser


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()

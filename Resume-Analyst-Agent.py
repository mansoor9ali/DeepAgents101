import json
import os
import re

from docling.document_converter import DocumentConverter
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
from langchain.agents.middleware import TodoListMiddleware
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith.wrappers import wrap_gemini

# Load environment variables
load_dotenv()


@tool
def read_resume(file_path: str) -> str:
    """Read a resume from the specified file path and return its content using Docling.

    Args:
        file_path: The path to the resume file to read (PDF, DOCX, etc.).
    """
    print(f"Reading resume from: {file_path}")
    try:
        # Initialize Docling converter
        converter = DocumentConverter()

        # Convert the document
        result = converter.convert(file_path)

        # Extract text content
        resume_text = result.document.export_to_markdown()

        print(f"Successfully read resume. Content length: {len(resume_text)} characters")
        return resume_text
    except Exception as e:
        error_msg = f"Error reading resume: {str(e)}"
        print(error_msg)
        return error_msg

@tool
def extract_information(resume_content: str) -> str:
    """Extract information such as name, contact, experience, skills, and education from resume content.

    Args:
        resume_content: The content of the resume to extract information from.
    """
    print("Extracting information from resume")

    try:
        extracted_data = {
            "name": "",
            "contact": {"email": "", "phone": "", "linkedin": "", "location": ""},
            "summary": "",
            "experience": [],
            "skills": [],
            "education": [],
            "certifications": [],
            "languages": []
        }

        lines = resume_content.split('\n')

        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, resume_content)
        if emails:
            extracted_data["contact"]["email"] = emails[0]

        # Extract phone numbers
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        phones = re.findall(phone_pattern, resume_content)
        if phones:
            extracted_data["contact"]["phone"] = phones[0].strip()

        # Extract LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin = re.findall(linkedin_pattern, resume_content.lower())
        if linkedin:
            extracted_data["contact"]["linkedin"] = linkedin[0]

        # Try to extract name (usually first non-empty line or largest text)
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 50 and not any(char.isdigit() for char in line):
                if '@' not in line and 'http' not in line.lower():
                    extracted_data["name"] = line
                    break

        # Extract sections
        current_section = ""
        section_content = []

        for line in lines:
            line_lower = line.lower().strip()

            # Identify sections
            if any(keyword in line_lower for keyword in ['experience', 'work history', 'employment']):
                if current_section == "experience" and section_content:
                    extracted_data["experience"].append('\n'.join(section_content))
                current_section = "experience"
                section_content = []
            elif any(keyword in line_lower for keyword in ['education', 'academic']):
                if current_section == "experience" and section_content:
                    extracted_data["experience"].append('\n'.join(section_content))
                current_section = "education"
                section_content = []
            elif any(keyword in line_lower for keyword in ['skills', 'technical skills', 'competencies']):
                if current_section and section_content:
                    if current_section == "experience":
                        extracted_data["experience"].append('\n'.join(section_content))
                    elif current_section == "education":
                        extracted_data["education"].append('\n'.join(section_content))
                current_section = "skills"
                section_content = []
            elif any(keyword in line_lower for keyword in ['summary', 'profile', 'objective']):
                current_section = "summary"
                section_content = []
            elif any(keyword in line_lower for keyword in ['certification', 'certificate']):
                if current_section and section_content:
                    if current_section == "experience":
                        extracted_data["experience"].append('\n'.join(section_content))
                    elif current_section == "education":
                        extracted_data["education"].append('\n'.join(section_content))
                current_section = "certifications"
                section_content = []
            elif any(keyword in line_lower for keyword in ['languages', 'language proficiency']):
                current_section = "languages"
                section_content = []
            elif line.strip():
                if current_section == "summary":
                    extracted_data["summary"] += " " + line.strip()
                elif current_section == "skills":
                    extracted_data["skills"].append(line.strip())
                elif current_section in ["experience", "education", "certifications", "languages"]:
                    section_content.append(line.strip())

        # Add remaining section content
        if current_section == "experience" and section_content:
            extracted_data["experience"].append('\n'.join(section_content))
        elif current_section == "education" and section_content:
            extracted_data["education"].append('\n'.join(section_content))
        elif current_section == "certifications" and section_content:
            extracted_data["certifications"] = section_content
        elif current_section == "languages" and section_content:
            extracted_data["languages"] = section_content

        print(f"Successfully extracted information. Name: {extracted_data['name']}")
        return json.dumps(extracted_data, indent=2)

    except Exception as e:
        error_msg = f"Error extracting information: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg})

@tool
def generate_summary(extracted_data: str) -> str:
    """Generate a comprehensive summary report based on extracted data from a resume.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
    """
    print("Generating summary report")

    try:
        # Parse the JSON string
        data = json.loads(extracted_data)

        # Build the summary report
        summary_parts = []

        # Header
        summary_parts.append("=" * 60)
        summary_parts.append("RESUME ANALYSIS SUMMARY")
        summary_parts.append("=" * 60)
        summary_parts.append("")

        # Personal Information
        summary_parts.append("📋 PERSONAL INFORMATION")
        summary_parts.append("-" * 60)
        if data.get("name"):
            summary_parts.append(f"Name: {data['name']}")

        contact = data.get("contact", {})
        if contact.get("email"):
            summary_parts.append(f"Email: {contact['email']}")
        if contact.get("phone"):
            summary_parts.append(f"Phone: {contact['phone']}")
        if contact.get("linkedin"):
            summary_parts.append(f"LinkedIn: {contact['linkedin']}")
        if contact.get("location"):
            summary_parts.append(f"Location: {contact['location']}")
        summary_parts.append("")

        # Professional Summary
        if data.get("summary"):
            summary_parts.append("💼 PROFESSIONAL SUMMARY")
            summary_parts.append("-" * 60)
            summary_parts.append(data["summary"].strip())
            summary_parts.append("")

        # Experience
        if data.get("experience"):
            summary_parts.append("🏢 WORK EXPERIENCE")
            summary_parts.append("-" * 60)
            for idx, exp in enumerate(data["experience"], 1):
                if exp.strip():
                    summary_parts.append(f"\n{idx}. {exp}")
            summary_parts.append("")

        # Skills
        if data.get("skills"):
            summary_parts.append("🛠️ SKILLS")
            summary_parts.append("-" * 60)
            skills_list = [s for s in data["skills"] if s.strip()]
            if skills_list:
                summary_parts.append(", ".join(skills_list[:20]))  # Limit to first 20 skills
            summary_parts.append("")

        # Education
        if data.get("education"):
            summary_parts.append("🎓 EDUCATION")
            summary_parts.append("-" * 60)
            for idx, edu in enumerate(data["education"], 1):
                if edu.strip():
                    summary_parts.append(f"{idx}. {edu}")
            summary_parts.append("")

        # Certifications
        if data.get("certifications"):
            summary_parts.append("📜 CERTIFICATIONS")
            summary_parts.append("-" * 60)
            for cert in data["certifications"]:
                if cert.strip():
                    summary_parts.append(f"• {cert}")
            summary_parts.append("")

        # Languages
        if data.get("languages"):
            summary_parts.append("🌐 LANGUAGES")
            summary_parts.append("-" * 60)
            for lang in data["languages"]:
                if lang.strip():
                    summary_parts.append(f"• {lang}")
            summary_parts.append("")

        # Key Insights
        summary_parts.append("💡 KEY INSIGHTS")
        summary_parts.append("-" * 60)
        insights = []

        if data.get("experience"):
            exp_count = len([e for e in data["experience"] if e.strip()])
            insights.append(f"• {exp_count} work experience entries documented")

        if data.get("skills"):
            skill_count = len([s for s in data["skills"] if s.strip()])
            insights.append(f"• {skill_count} skills identified")

        if data.get("education"):
            edu_count = len([e for e in data["education"] if e.strip()])
            insights.append(f"• {edu_count} educational qualifications listed")

        if data.get("certifications"):
            cert_count = len([c for c in data["certifications"] if c.strip()])
            insights.append(f"• {cert_count} certifications obtained")

        summary_parts.extend(insights)
        summary_parts.append("")
        summary_parts.append("=" * 60)

        summary = "\n".join(summary_parts)
        print("Summary report generated successfully")
        return summary

    except json.JSONDecodeError as e:
        error_msg = f"Error parsing extracted data: {str(e)}\nReceived data: {extracted_data[:200]}..."
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error generating summary: {str(e)}"
        print(error_msg)
        return error_msg

@tool
def calculate_experience_years(extracted_data: str) -> str:
    """Calculate total years of experience from the extracted resume data.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
    """
    print("Calculating years of experience")

    try:
        data = json.loads(extracted_data)
        experience_entries = data.get("experience", [])

        # Common year patterns
        year_pattern = r'\b(19|20)\d{2}\b'
        duration_pattern = r'(\d+)\s*(year|yr|years|yrs)'

        total_years = 0
        year_ranges = []

        for exp in experience_entries:
            # Look for year ranges (e.g., "2020 - 2023" or "2020-Present")
            years = re.findall(year_pattern, exp)
            if len(years) >= 2:
                start_year = int(years[0])
                end_year = int(years[1]) if years[1] else 2026
                duration = end_year - start_year
                year_ranges.append((start_year, end_year, duration))
                total_years += duration

            # Look for explicit duration mentions
            durations = re.findall(duration_pattern, exp.lower())
            for duration, _ in durations:
                total_years += int(duration)

        result = {
            "total_years": total_years,
            "year_ranges": year_ranges,
            "experience_count": len(experience_entries)
        }

        report = f"Total Years of Experience: {total_years}\n"
        report += f"Number of Positions: {len(experience_entries)}\n"
        if year_ranges:
            report += "\nExperience Timeline:\n"
            for start, end, duration in year_ranges:
                end_str = "Present" if end == 2026 else str(end)
                report += f"  • {start} - {end_str} ({duration} years)\n"

        print(f"Calculated {total_years} years of experience")
        return report

    except Exception as e:
        error_msg = f"Error calculating experience: {str(e)}"
        print(error_msg)
        return error_msg

@tool
def match_job_requirements(extracted_data: str, job_requirements: str) -> str:
    """Match resume skills and experience against job requirements.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
        job_requirements: A string describing the job requirements to match against.
    """
    print("Matching resume against job requirements")

    try:
        data = json.loads(extracted_data)
        resume_skills = [skill.lower().strip() for skill in data.get("skills", []) if skill.strip()]

        # Extract keywords from job requirements
        job_req_lower = job_requirements.lower()
        job_keywords = set()

        # Common tech skills and keywords
        common_skills = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node', 'django', 'flask', 'spring', 'sql', 'nosql', 'mongodb', 'postgresql',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'ci/cd', 'git', 'agile',
            'scrum', 'machine learning', 'ai', 'data science', 'analytics', 'leadership',
            'communication', 'project management', 'api', 'rest', 'microservices'
        ]

        for skill in common_skills:
            if skill in job_req_lower:
                job_keywords.add(skill)

        # Match resume skills against job keywords
        matched_skills = []
        missing_skills = []

        for keyword in job_keywords:
            if any(keyword in resume_skill for resume_skill in resume_skills):
                matched_skills.append(keyword)
            else:
                missing_skills.append(keyword)

        # Calculate match percentage
        total_keywords = len(job_keywords)
        match_percentage = (len(matched_skills) / total_keywords * 100) if total_keywords > 0 else 0

        # Build report
        report_parts = []
        report_parts.append("=" * 60)
        report_parts.append("JOB REQUIREMENTS MATCH ANALYSIS")
        report_parts.append("=" * 60)
        report_parts.append("")
        report_parts.append(f"📊 Match Score: {match_percentage:.1f}%")
        report_parts.append("")

        if matched_skills:
            report_parts.append("✅ MATCHING SKILLS:")
            for skill in matched_skills:
                report_parts.append(f"  • {skill}")
            report_parts.append("")

        if missing_skills:
            report_parts.append("❌ MISSING SKILLS:")
            for skill in missing_skills:
                report_parts.append(f"  • {skill}")
            report_parts.append("")

        report_parts.append("💡 RECOMMENDATIONS:")
        if match_percentage >= 70:
            report_parts.append("  • Strong match! Consider applying for this position.")
        elif match_percentage >= 50:
            report_parts.append("  • Good match. Consider highlighting relevant experience.")
        else:
            report_parts.append("  • Consider acquiring missing skills or emphasizing transferable skills.")

        report_parts.append("=" * 60)

        report = "\n".join(report_parts)
        print(f"Match analysis complete. Score: {match_percentage:.1f}%")
        return report

    except Exception as e:
        error_msg = f"Error matching job requirements: {str(e)}"
        print(error_msg)
        return error_msg

@tool
def suggest_improvements(extracted_data: str) -> str:
    """Provide actionable suggestions to improve the resume.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
    """
    print("Generating improvement suggestions")

    try:
        data = json.loads(extracted_data)
        suggestions = []

        # Check name
        if not data.get("name"):
            suggestions.append("⚠️ Name is missing or not clearly visible. Ensure your name is prominent at the top.")

        # Check contact information
        contact = data.get("contact", {})
        if not contact.get("email"):
            suggestions.append("⚠️ Email address is missing. Add a professional email address.")
        if not contact.get("phone"):
            suggestions.append("💡 Consider adding a phone number for easy contact.")
        if not contact.get("linkedin"):
            suggestions.append("💡 Add your LinkedIn profile URL to strengthen your professional presence.")

        # Check summary
        if not data.get("summary"):
            suggestions.append("⚠️ Professional summary is missing. Add a 2-3 sentence summary highlighting your expertise.")
        elif len(data.get("summary", "")) < 100:
            suggestions.append("💡 Your professional summary is brief. Expand it to better showcase your value proposition.")

        # Check experience
        experience = data.get("experience", [])
        if not experience:
            suggestions.append("⚠️ Work experience section is missing or not detected. This is a critical section.")
        elif len(experience) < 2:
            suggestions.append("💡 Consider adding more detailed work experience entries with achievements and metrics.")

        # Check skills
        skills = [s for s in data.get("skills", []) if s.strip()]
        if not skills:
            suggestions.append("⚠️ Skills section is missing or not detected. Add a dedicated skills section.")
        elif len(skills) < 5:
            suggestions.append("💡 Add more relevant skills to increase your visibility in applicant tracking systems.")

        # Check education
        if not data.get("education"):
            suggestions.append("⚠️ Education section is missing or not detected. Include your educational background.")

        # Check certifications
        if not data.get("certifications"):
            suggestions.append("💡 Consider adding relevant certifications to strengthen your credentials.")

        # General suggestions
        suggestions.append("")
        suggestions.append("✨ GENERAL BEST PRACTICES:")
        suggestions.append("  • Use action verbs (Led, Developed, Implemented, Achieved)")
        suggestions.append("  • Include quantifiable achievements (e.g., 'Increased revenue by 30%')")
        suggestions.append("  • Keep formatting consistent throughout the document")
        suggestions.append("  • Tailor your resume for each job application")
        suggestions.append("  • Keep it concise (1-2 pages for most professionals)")
        suggestions.append("  • Use keywords from job descriptions to pass ATS systems")

        # Build report
        report_parts = []
        report_parts.append("=" * 60)
        report_parts.append("RESUME IMPROVEMENT SUGGESTIONS")
        report_parts.append("=" * 60)
        report_parts.append("")
        report_parts.extend(suggestions)
        report_parts.append("")
        report_parts.append("=" * 60)

        report = "\n".join(report_parts)
        print(f"Generated {len(suggestions)} improvement suggestions")
        return report

    except Exception as e:
        error_msg = f"Error generating suggestions: {str(e)}"
        print(error_msg)
        return error_msg

# System prompt for the Resume Analysis Agent
# system_prompt = """You are a professional resume analysis expert specializing in evaluating and improving resumes.
# **Your Responsibilities:**
# 1. Analyze and assess the overall quality and effectiveness of resumes.
# 2. Provide insights on work experience, skills, and education.
# 3. Offer constructive feedback and suggestions for enhancing resumes.
# 4. Use available tools to extract and analyze key information.
# **Analysis Framework:**
# - Personal Information: Name, Contact, LinkedIn Profile
# - Professional Summary: Key achievements and career goals
# - Work Experience: Roles, responsibilities, and achievements
# - Skills: Technical and soft skills relevant to the industry
# - Education: Degrees, certifications, and relevant coursework
# - Additional Sections: Awards, publications, languages
# - Overall Format and Style: Clarity, conciseness, and professionalism
# **Important Guidelines:**
# - Only respond to questions related to resume analysis and improvement.
# - For non-relevant questions, politely decline: "I apologize, but I can only assist with resume analysis and improvement. Please ask me about resume-related queries."
# - Always provide specific examples and metrics when giving feedback.
# - Maintain a supportive and constructive tone.
# Provide clear, actionable suggestions that help individuals enhance their resumes for potential employers."""
# Improved System Prompt for the Resume Analysis Agent
system_prompt = """You are a professional resume analysis expert specializing in evaluating and improving resumes across diverse industries.
**Your Responsibilities:**
1. Thoroughly analyze and assess the overall quality and effectiveness of resumes.
2. Provide insights on work experience, skills, and education, tailored to specific industries.
3. Offer constructive feedback and actionable suggestions for enhancing resumes, ensuring feedback is positive and educational.
4. Dynamically utilize available tools to extract and analyze key information based on the resume context.
5. Continuously update advice with the latest industry trends and job market requirements.
**Analysis Framework:**
- Personal Information: Name, Contact, LinkedIn Profile
- Professional Summary: Key achievements and career goals, emphasizing quantifiable outcomes
- Work Experience: Roles, responsibilities, and achievements, highlighted with specific metrics
- Skills: Technical and soft skills pertinent to the industry
- Education: Degrees, certifications, and relevant coursework aligned with role requirements
- Additional Sections: Awards, publications, languages, with attention to detail and relevance
- Overall Format and Style: Clarity, conciseness, and professionalism consistent with industry standards
**Important Guidelines:**
- Respond exclusively to queries related to resume analysis and improvement.
- For non-relevant questions, politely respond: "I apologize, but I can only assist with resume analysis and improvement. Please ask me about resume-related queries."
- Provide specific examples and metrics to illustrate feedback effectively.
- Maintain a supportive and constructive tone, fostering improvement and growth.
- Encourage the use of industry standards and current job market trends when formulating recommendations.
Deliver clear, actionable insights that empower individuals to enhance their resumes for potential employers, adapting to varied professional and industry contexts."""

MODEL_NAME = os.getenv("RESUME_AGENT_MODEL", 'gemini-3-pro-preview')

# Initialize the model
model = wrap_gemini(ChatGoogleGenerativeAI(model='gemini-3-pro-preview'))

# Create the ReAct agent with resume analysis tools
# This is the graph that LangGraph Server will serve
# Create an agent for resume analysis with the defined system prompt and tools
agent = create_agent(
    model=model,
    tools=[
        read_resume,
        extract_information,
        generate_summary,
        calculate_experience_years,
        match_job_requirements,
        suggest_improvements,
    ],
    middleware=[TodoListMiddleware(),
                PIIMiddleware("email", strategy="redact", apply_to_input=True),
                PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
                PIIMiddleware("url", strategy="redact", apply_to_input=True)],
    # Middleware can be customized if needed
    system_prompt=system_prompt  # Use the custom system prompt
)


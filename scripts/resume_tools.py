"""
Resume Analysis Tools
Reusable tools for resume parsing, extraction, and analysis.
"""

import json
import re
from langchain.tools import tool
from docling.document_converter import DocumentConverter


@tool
def read_resume(file_path: str) -> str:
    """Read a resume from the specified file path and return its content using Docling.

    Args:
        file_path: The path to the resume file to read (PDF, DOCX, etc.).
    """
    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        resume_text = result.document.export_to_markdown()
        return resume_text
    except Exception as e:
        return f"Error reading resume: {str(e)}"


@tool
def extract_information(resume_content: str) -> str:
    """Extract information such as name, contact, experience, skills, and education from resume content.

    Args:
        resume_content: The content of the resume to extract information from.
    """
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

        # Try to extract name
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

        return json.dumps(extracted_data, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def generate_summary(extracted_data: str) -> str:
    """Generate a comprehensive summary report based on extracted data from a resume.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
    """
    try:
        data = json.loads(extracted_data)
        summary_parts = []

        summary_parts.append("# 📋 RESUME ANALYSIS SUMMARY\n")

        # Personal Information
        summary_parts.append("## 👤 Personal Information\n")
        if data.get("name"):
            summary_parts.append(f"**Name:** {data['name']}\n")

        contact = data.get("contact", {})
        if contact.get("email"):
            summary_parts.append(f"**Email:** {contact['email']}\n")
        if contact.get("phone"):
            summary_parts.append(f"**Phone:** {contact['phone']}\n")
        if contact.get("linkedin"):
            summary_parts.append(f"**LinkedIn:** {contact['linkedin']}\n")
        if contact.get("location"):
            summary_parts.append(f"**Location:** {contact['location']}\n")

        # Professional Summary
        if data.get("summary"):
            summary_parts.append("\n## 💼 Professional Summary\n")
            summary_parts.append(data["summary"].strip() + "\n")

        # Experience
        if data.get("experience"):
            summary_parts.append("\n## 🏢 Work Experience\n")
            for idx, exp in enumerate(data["experience"], 1):
                if exp.strip():
                    summary_parts.append(f"### Position {idx}\n{exp}\n")

        # Skills
        if data.get("skills"):
            summary_parts.append("\n## 🛠️ Skills\n")
            skills_list = [s for s in data["skills"] if s.strip()]
            if skills_list:
                summary_parts.append(", ".join(skills_list[:20]) + "\n")

        # Education
        if data.get("education"):
            summary_parts.append("\n## 🎓 Education\n")
            for idx, edu in enumerate(data["education"], 1):
                if edu.strip():
                    summary_parts.append(f"{idx}. {edu}\n")

        # Certifications
        if data.get("certifications"):
            summary_parts.append("\n## 📜 Certifications\n")
            for cert in data["certifications"]:
                if cert.strip():
                    summary_parts.append(f"- {cert}\n")

        # Languages
        if data.get("languages"):
            summary_parts.append("\n## 🌐 Languages\n")
            for lang in data["languages"]:
                if lang.strip():
                    summary_parts.append(f"- {lang}\n")

        # Key Insights
        summary_parts.append("\n## 💡 Key Insights\n")
        if data.get("experience"):
            exp_count = len([e for e in data["experience"] if e.strip()])
            summary_parts.append(f"- {exp_count} work experience entries documented\n")
        if data.get("skills"):
            skill_count = len([s for s in data["skills"] if s.strip()])
            summary_parts.append(f"- {skill_count} skills identified\n")
        if data.get("education"):
            edu_count = len([e for e in data["education"] if e.strip()])
            summary_parts.append(f"- {edu_count} educational qualifications listed\n")
        if data.get("certifications"):
            cert_count = len([c for c in data["certifications"] if c.strip()])
            summary_parts.append(f"- {cert_count} certifications obtained\n")

        return "".join(summary_parts)

    except json.JSONDecodeError as e:
        return f"Error parsing extracted data: {str(e)}"
    except Exception as e:
        return f"Error generating summary: {str(e)}"


@tool
def calculate_experience_years(extracted_data: str) -> str:
    """Calculate total years of experience from the extracted resume data.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
    """
    try:
        data = json.loads(extracted_data)
        experience_entries = data.get("experience", [])

        year_pattern = r'\b(19|20)\d{2}\b'
        total_years = 0
        year_ranges = []

        for exp in experience_entries:
            years = re.findall(year_pattern, exp)
            if len(years) >= 2:
                start_year = int(years[0])
                end_year = int(years[1]) if years[1] else 2026
                duration = end_year - start_year
                year_ranges.append((start_year, end_year, duration))
                total_years += duration

        report = f"**Total Years of Experience:** {total_years}\n"
        report += f"**Number of Positions:** {len(experience_entries)}\n"
        if year_ranges:
            report += "\n**Experience Timeline:**\n"
            for start, end, duration in year_ranges:
                end_str = "Present" if end == 2026 else str(end)
                report += f"- {start} - {end_str} ({duration} years)\n"

        return report

    except Exception as e:
        return f"Error calculating experience: {str(e)}"


@tool
def match_job_requirements(extracted_data: str, job_requirements: str) -> str:
    """Match resume skills and experience against job requirements.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
        job_requirements: A string describing the job requirements to match against.
    """
    try:
        data = json.loads(extracted_data)
        resume_skills = [skill.lower().strip() for skill in data.get("skills", []) if skill.strip()]

        job_req_lower = job_requirements.lower()
        job_keywords = set()

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

        matched_skills = []
        missing_skills = []

        for keyword in job_keywords:
            if any(keyword in resume_skill for resume_skill in resume_skills):
                matched_skills.append(keyword)
            else:
                missing_skills.append(keyword)

        total_keywords = len(job_keywords)
        match_percentage = (len(matched_skills) / total_keywords * 100) if total_keywords > 0 else 0

        report_parts = []
        report_parts.append("# 📊 Job Requirements Match Analysis\n")
        report_parts.append(f"## Match Score: {match_percentage:.1f}%\n")

        if matched_skills:
            report_parts.append("\n### ✅ Matching Skills\n")
            for skill in matched_skills:
                report_parts.append(f"- {skill}\n")

        if missing_skills:
            report_parts.append("\n### ❌ Missing Skills\n")
            for skill in missing_skills:
                report_parts.append(f"- {skill}\n")

        report_parts.append("\n### 💡 Recommendations\n")
        if match_percentage >= 70:
            report_parts.append("- Strong match! Consider applying for this position.\n")
        elif match_percentage >= 50:
            report_parts.append("- Good match. Consider highlighting relevant experience.\n")
        else:
            report_parts.append("- Consider acquiring missing skills or emphasizing transferable skills.\n")

        return "".join(report_parts)

    except Exception as e:
        return f"Error matching job requirements: {str(e)}"


@tool
def suggest_improvements(extracted_data: str) -> str:
    """Provide actionable suggestions to improve the resume.

    Args:
        extracted_data: A JSON string containing extracted information from the resume.
    """
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

        # Build report
        report_parts = []
        report_parts.append("# 📝 Resume Improvement Suggestions\n")

        if suggestions:
            report_parts.append("## Areas for Improvement\n")
            for suggestion in suggestions:
                report_parts.append(f"- {suggestion}\n")

        report_parts.append("\n## ✨ General Best Practices\n")
        report_parts.append("- Use action verbs (Led, Developed, Implemented, Achieved)\n")
        report_parts.append("- Include quantifiable achievements (e.g., 'Increased revenue by 30%')\n")
        report_parts.append("- Keep formatting consistent throughout the document\n")
        report_parts.append("- Tailor your resume for each job application\n")
        report_parts.append("- Keep it concise (1-2 pages for most professionals)\n")
        report_parts.append("- Use keywords from job descriptions to pass ATS systems\n")

        return "".join(report_parts)

    except Exception as e:
        return f"Error generating suggestions: {str(e)}"


# List of all resume tools for easy import
RESUME_TOOLS = [
    read_resume,
    extract_information,
    generate_summary,
    calculate_experience_years,
    match_job_requirements,
    suggest_improvements,
]

# System prompt for the Resume Analysis Agent
RESUME_AGENT_SYSTEM_PROMPT = """You are a professional resume analysis expert specializing in evaluating and improving resumes across diverse industries.

**Your Responsibilities:**
1. Thoroughly analyze and assess the overall quality and effectiveness of resumes.
2. Provide insights on work experience, skills, and education, tailored to specific industries.
3. Offer constructive feedback and actionable suggestions for enhancing resumes.
4. Dynamically utilize available tools to extract and analyze key information based on the resume context.

**Analysis Framework:**
- Personal Information: Name, Contact, LinkedIn Profile
- Professional Summary: Key achievements and career goals
- Work Experience: Roles, responsibilities, and achievements
- Skills: Technical and soft skills pertinent to the industry
- Education: Degrees, certifications, and relevant coursework
- Additional Sections: Awards, publications, languages
- Overall Format and Style: Clarity, conciseness, and professionalism

**Important Guidelines:**
- Respond exclusively to queries related to resume analysis and improvement.
- Provide specific examples and metrics to illustrate feedback effectively.
- Maintain a supportive and constructive tone.
- Format your responses in clean Markdown for better readability.

Deliver clear, actionable insights that empower individuals to enhance their resumes for potential employers."""


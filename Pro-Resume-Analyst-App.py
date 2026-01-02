"""
Pro Resume Analyst - Streamlit Application
A professional resume analysis tool powered by AI
"""

import os
import tempfile
import time
from dotenv import load_dotenv

import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langsmith.wrappers import wrap_gemini

# Import utilities from scripts folder
from scripts.resume_tools import RESUME_TOOLS, RESUME_AGENT_SYSTEM_PROMPT
from scripts.pdf_utils import create_pdf_from_markdown, is_pdf_available

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Pro Resume Analyst",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #1E88E5;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
    .result-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        max-height: 600px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)



@st.cache_resource
def get_agent():
    """Create and cache the resume analysis agent."""
    model = wrap_gemini(ChatGoogleGenerativeAI(model='gemini-2.0-flash'))

    agent = create_agent(
        model=model,
        tools=RESUME_TOOLS,
        system_prompt=RESUME_AGENT_SYSTEM_PROMPT
    )
    return agent


def run_analysis(file_path: str, job_requirements: str = None) -> str:
    """Run the resume analysis."""
    agent = get_agent()

    if job_requirements:
        prompt = f"Analyze the resume from file: {file_path}. Also match it against these job requirements: {job_requirements}"
    else:
        prompt = f"Analyze the resume from file: {file_path}. Provide a comprehensive analysis including personal information extraction, experience summary, skills assessment, and improvement suggestions."

    response = agent.invoke({'messages': [prompt]})
    return response['messages'][-1].text


def main():
    """Main application."""
    # Header
    st.markdown('<h1 class="main-header">📄 Pro Resume Analyst</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Resume Analysis & Improvement Suggestions</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown("---")

        # Optional job requirements input
        st.subheader("📋 Job Requirements (Optional)")
        job_requirements = st.text_area(
            "Paste job requirements to match:",
            placeholder="e.g., 5+ years Python experience, AWS certification, leadership skills...",
            height=150
        )

        st.markdown("---")
        st.markdown("### 📌 How to Use")
        st.markdown("""
        1. Upload your resume (PDF, DOCX)
        2. Optionally add job requirements
        3. Click 'Analyze Resume'
        4. View results & download PDF
        """)

        st.markdown("---")
        st.markdown("### 📊 Supported Formats")
        st.markdown("- PDF Documents")
        st.markdown("- Word Documents (.docx)")
        st.markdown("- Text Files (.txt)")

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Upload Resume")

        uploaded_file = st.file_uploader(
            "Choose your resume file",
            type=['pdf', 'docx', 'txt'],
            help="Upload a PDF, DOCX, or TXT file"
        )

        if uploaded_file is not None:
            st.success(f"✅ File uploaded: **{uploaded_file.name}**")
            st.info(f"📊 File size: {uploaded_file.size / 1024:.2f} KB")

            analyze_button = st.button("🔍 Analyze Resume", type="primary", use_container_width=True)

            if analyze_button:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                try:
                    # Processing animation
                    with st.status("🔄 Analyzing your resume...", expanded=True) as status:
                        st.write("📖 Reading document...")
                        time.sleep(0.5)

                        progress_bar = st.progress(0)

                        # Simulate progress steps
                        steps = [
                            ("📝 Extracting text content...", 10),
                            ("🔍 Identifying key sections...", 25),
                            ("👤 Extracting personal information...", 40),
                            ("💼 Analyzing work experience...", 55),
                            ("🛠️ Evaluating skills...", 70),
                            ("🎓 Processing education details...", 80),
                            ("💡 Generating insights...", 90),
                            ("✨ Finalizing analysis...", 100),
                        ]

                        for step_text, progress in steps:
                            st.write(step_text)
                            progress_bar.progress(progress)
                            time.sleep(0.3)

                        # Run actual analysis
                        st.write("🤖 AI Agent is analyzing...")
                        result = run_analysis(tmp_path, job_requirements if job_requirements else None)

                        status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

                    # Store result in session state
                    st.session_state['analysis_result'] = result
                    st.session_state['file_name'] = uploaded_file.name

                except Exception as e:
                    st.error(f"❌ Error during analysis: {str(e)}")
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    with col2:
        st.header("📊 Analysis Results")

        if 'analysis_result' in st.session_state:
            result = st.session_state['analysis_result']
            file_name = st.session_state.get('file_name', 'resume')

            # Display markdown result in a container
            with st.container():
                st.markdown(
                    f'<div class="result-container">{result}</div>',
                    unsafe_allow_html=True
                )

                # Actually render the markdown properly
                with st.expander("📄 View Full Analysis", expanded=True):
                    st.markdown(result)

            # Download options
            st.markdown("---")
            st.subheader("📥 Download Options")

            col_a, col_b = st.columns(2)

            with col_a:
                # Download as Markdown
                st.download_button(
                    label="📝 Download as Markdown",
                    data=result,
                    file_name=f"{os.path.splitext(file_name)[0]}_analysis.md",
                    mime="text/markdown",
                    use_container_width=True
                )

            with col_b:
                # Download as PDF
                if is_pdf_available():
                    try:
                        pdf_bytes = create_pdf_from_markdown(result)
                        st.download_button(
                            label="📄 Download as PDF",
                            data=pdf_bytes,
                            file_name=f"{os.path.splitext(file_name)[0]}_analysis.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.warning(f"PDF generation unavailable: {str(e)}")
                else:
                    st.info("💡 Install `fpdf` for PDF export: `pip install fpdf`")
        else:
            st.info("👆 Upload a resume and click 'Analyze Resume' to see results here.")

            # Placeholder with animation
            st.markdown("""
            <div style="text-align: center; padding: 3rem; color: #666;">
                <h3>🎯 Ready to Analyze</h3>
                <p>Your analysis results will appear here</p>
            </div>
            """, unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #666;">Powered by AI | Pro Resume Analyst © 2026</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()


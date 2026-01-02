"""
PDF Utilities
Reusable functions for PDF generation from markdown content.
"""

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


def is_pdf_available() -> bool:
    """Check if PDF generation is available."""
    return FPDF_AVAILABLE


def create_pdf_from_markdown(markdown_content: str) -> bytes:
    """
    Create a PDF from markdown content.

    Args:
        markdown_content: The markdown content to convert to PDF.

    Returns:
        bytes: The PDF content as bytes.

    Raises:
        ImportError: If fpdf is not installed.
        Exception: If PDF generation fails.
    """
    if not FPDF_AVAILABLE:
        raise ImportError("fpdf is not installed. Run: pip install fpdf")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Set font
    pdf.set_font("Arial", size=10)

    # Process markdown content
    lines = markdown_content.split('\n')

    for line in lines:
        # Handle headers
        if line.startswith('# '):
            pdf.set_font("Arial", 'B', 16)
            pdf.multi_cell(0, 10, line[2:].encode('latin-1', 'replace').decode('latin-1'))
            pdf.set_font("Arial", size=10)
        elif line.startswith('## '):
            pdf.set_font("Arial", 'B', 14)
            pdf.multi_cell(0, 8, line[3:].encode('latin-1', 'replace').decode('latin-1'))
            pdf.set_font("Arial", size=10)
        elif line.startswith('### '):
            pdf.set_font("Arial", 'B', 12)
            pdf.multi_cell(0, 7, line[4:].encode('latin-1', 'replace').decode('latin-1'))
            pdf.set_font("Arial", size=10)
        elif line.startswith('- '):
            pdf.multi_cell(0, 5, "  " + chr(149) + " " + line[2:].encode('latin-1', 'replace').decode('latin-1'))
        elif line.startswith('**') and line.endswith('**'):
            pdf.set_font("Arial", 'B', 10)
            pdf.multi_cell(0, 5, line[2:-2].encode('latin-1', 'replace').decode('latin-1'))
            pdf.set_font("Arial", size=10)
        elif line.strip():
            # Handle inline bold
            clean_line = line.replace('**', '')
            pdf.multi_cell(0, 5, clean_line.encode('latin-1', 'replace').decode('latin-1'))
        else:
            pdf.ln(3)

    return pdf.output(dest='S').encode('latin-1')


def create_simple_pdf(title: str, content: str) -> bytes:
    """
    Create a simple PDF with a title and content.

    Args:
        title: The title of the PDF document.
        content: The text content of the PDF.

    Returns:
        bytes: The PDF content as bytes.
    """
    if not FPDF_AVAILABLE:
        raise ImportError("fpdf is not installed. Run: pip install fpdf")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(10)

    # Content
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, content.encode('latin-1', 'replace').decode('latin-1'))

    return pdf.output(dest='S').encode('latin-1')


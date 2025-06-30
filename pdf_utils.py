import PyPDF2

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from an uploaded PDF file"""
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text
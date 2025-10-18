
import PyPDF2
import pdfplumber
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from an uploaded PDF file, supporting English and Bengali scripts."""
    try:
        # Initialize PDF reader
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        
        # Check if PDF is encrypted
        if pdf_reader.is_encrypted:
            st.error("Cannot process encrypted PDF. Please provide an unencrypted file.")
            return ""
        
        text = ""
        # Try pdfplumber first
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text
        except Exception as e:
            st.warning(f"pdfplumber failed: {str(e)}. Falling back to PyPDF2.")
            # Fallback to PyPDF2
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                text += page_text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        
        # If no text extracted, try OCR with pytesseract
        if not text.strip():
            st.warning("No text extracted. Attempting OCR with pytesseract...")
            uploaded_file.seek(0)  # Reset file pointer
            images = convert_from_bytes(uploaded_file.read())
            for image in images:
                text += pytesseract.image_to_string(image, lang='ben')  # Use Bengali OCR
            if not text.strip():
                st.warning("OCR failed to extract text. PDF may contain unsupported formatting.")
        
        if not text.strip():
            st.warning("No text could be extracted from the PDF.")
        
        return text
    
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

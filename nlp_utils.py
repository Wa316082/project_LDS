import re
from typing import List, Dict
import PyPDF2
from collections import defaultdict

# Document preprocessing
def preprocess_text(text: str) -> str:
    """Clean and normalize document text"""
    # Remove excessive whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    # Basic cleaning
    text = re.sub(r'\[.*?\]', '', text)  # Remove citations like [1]
    text = re.sub(r'\(.*?\)', '', text)  # Remove text in parentheses
    return text

# Extract text from PDF
def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text content from PDF files"""
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return preprocess_text(text)

# Clause segmentation
def segment_clauses(doc) -> List[str]:
    """Split document into logical clauses/sections"""
    clauses = []
    current_clause = ""
    
    # Split by common legal document patterns
    patterns = [
        r'\nSECTION\s+\d+[.:]',
        r'\nArticle\s+\d+[.:]',
        r'\n\d+\.\s',  # Numbered clauses
        r'\n\([a-z]\)',  # Lettered sub-clauses
        r'\nWHEREAS',  # Common contract preamble
    ]
    
    split_regex = re.compile('|'.join(patterns))
    parts = split_regex.split(doc)
    matches = split_regex.findall(doc)
    
    if len(parts) > 1:
        # The first part is usually preamble
        clauses.append(("Preamble", parts[0].strip()))
        for i in range(1, len(parts)):
            clause_title = matches[i-1].strip() if i <= len(matches) else f"Clause {i}"
            clauses.append((clause_title, parts[i].strip()))
    else:
        # Fallback: split by paragraphs
        paragraphs = [p.strip() for p in doc.split('\n') if p.strip()]
        for i, para in enumerate(paragraphs):
            clauses.append((f"Paragraph {i+1}", para))
    
    return clauses

# Classify clause type
def classify_clause(text: str, tokenizer, model) -> str:
    """Classify the type of legal clause"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    outputs = model(**inputs)
    predicted_class = outputs.logits.argmax().item()
    
    # Map to common legal clause types
    class_mapping = {
        0: "Definitions",
        1: "Obligations",
        2: "Rights",
        3: "Termination",
        4: "Confidentiality",
        5: "Payment Terms",
        6: "Governing Law",
        7: "Liability",
        8: "Data Protection",
        9: "Miscellaneous"
    }
    
    return class_mapping.get(predicted_class, "Unknown")

# Extract important points
def extract_important_points(text: str, nlp) -> List[str]:
    """Extract key sentences using linguistic features"""
    doc = nlp(text)
    important_points = []
    
    # Rules for important sentences
    for sent in doc.sents:
        # Check for modal verbs (shall, must, etc.)
        has_modal = any(tok.lower_ in ["shall", "must", "will", "may not", "cannot"] for tok in sent)
        
        # Check for legal phrases
        legal_phrases = ["hereby", "notwithstanding", "subject to", "in accordance with"]
        has_legal_phrase = any(phrase in sent.text.lower() for phrase in legal_phrases)
        
        # Check for defined terms (capitalized terms)
        # has_defined_terms = any(tok.is_upper() and len(tok.text) > 3 for tok in sent)
        has_defined_terms = any(tok.is_upper and len(tok.text) > 3 for tok in sent)

        
        if has_modal or has_legal_phrase or has_defined_terms:
            important_points.append(sent.text.strip())
    
    return important_points[:5]  # Return top 5 important points

# Extract obligations
def extract_obligations(text: str, nlp) -> Dict[str, List[str]]:
    """Identify obligations for each party"""
    doc = nlp(text)
    obligations = defaultdict(list)
    current_party = None
    
    for sent in doc.sents:
        # Simple pattern matching for obligations
        if "shall" in sent.text.lower() or "must" in sent.text.lower():
            # Try to find the subject (party with obligation)
            for tok in sent:
                if tok.dep_ in ("nsubj", "nsubjpass") and tok.ent_type_ == "ORG":
                    current_party = tok.text
                    break
            
            if current_party:
                obligations[current_party].append(sent.text.strip())
            else:
                obligations["All Parties"].append(sent.text.strip())
    
    return dict(obligations)

# Summarize clause
def summarize_clause(text: str, summarizer) -> str:
    """Generate concise summary of clause"""
    # Skip empty or very short texts
    if not text.strip() or len(text.split()) < 10:
        return text[:200] + "..." if len(text) > 200 else text
    
    try:
        # Ensure text isn't too long for the model
        if len(text.split()) > 1024:  # BART's typical max length
            text = ' '.join(text.split()[:1000])
            
        summary = summarizer(text, max_length=130, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"Summarization failed: {e}")
        return text[:200] + "..." if len(text) > 200 else text

# Extract dates and deadlines
def extract_dates(text: str, nlp) -> List[str]:
    """Extract important dates from text"""
    doc = nlp(text)
    dates = []
    
    for ent in doc.ents:
        if ent.label_ == "DATE":
            dates.append(ent.text)
    
    return dates
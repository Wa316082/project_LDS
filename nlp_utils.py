import re
from collections import defaultdict
from typing import Dict, List

import PyPDF2


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
def classify_clause(text: str, tokenizer=None, model=None) -> Dict[str, str]:
    """Classify the type of legal clause using both ML and rule-based approaches"""
    
    # Rule-based classification as fallback or primary method
    clause_keywords = {
        "Definitions": ["definition", "means", "shall mean", "defined as", "refers to", "includes"],
        "Obligations": ["shall", "must", "required to", "obligation", "duty", "responsible for"],
        "Rights": ["right to", "entitled to", "may", "permitted to", "authorized"],
        "Termination": ["terminate", "termination", "end", "expiry", "dissolution"],
        "Confidentiality": ["confidential", "non-disclosure", "proprietary", "trade secret"],
        "Payment Terms": ["payment", "fee", "cost", "price", "billing", "invoice"],
        "Governing Law": ["governing law", "jurisdiction", "applicable law", "courts"],
        "Liability": ["liable", "liability", "damages", "loss", "responsible for harm"],
        "Data Protection": ["personal data", "privacy", "data protection", "information"],
        "Intellectual Property": ["copyright", "trademark", "patent", "intellectual property"],
        "Dispute Resolution": ["dispute", "arbitration", "mediation", "resolution"],
        "Force Majeure": ["force majeure", "acts of god", "circumstances beyond control"],
        "Miscellaneous": []
    }
    
    text_lower = text.lower()
    scores = {}
    
    # Calculate scores for each category
    for category, keywords in clause_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if keywords:  # Don't score miscellaneous based on keywords
            scores[category] = score
    
    # Get best match
    if scores:
        best_category = max(scores.items(), key=lambda x: x[1])
        if best_category[1] > 0:
            classification = best_category[0]
        else:
            classification = "Miscellaneous"
    else:
        classification = "Miscellaneous"
    
    # If model is available, use it for additional insight
    confidence = "Medium"
    if tokenizer and model:
        try:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = model(**inputs)
            predicted_class = outputs.logits.argmax().item()
            
            class_mapping = {
                0: "Definitions", 1: "Obligations", 2: "Rights", 3: "Termination",
                4: "Confidentiality", 5: "Payment Terms", 6: "Governing Law",
                7: "Liability", 8: "Data Protection", 9: "Miscellaneous"
            }
            
            ml_classification = class_mapping.get(predicted_class, "Unknown")
            
            # Use ML result if it matches rule-based or if rule-based is uncertain
            if ml_classification == classification or classification == "Miscellaneous":
                classification = ml_classification
                confidence = "High"
                
        except Exception as e:
            print(f"ML classification failed: {e}")
    
    # Add explanation
    explanations = {
        "Definitions": "Contains definitions of terms used throughout the document",
        "Obligations": "Specifies duties and requirements that parties must fulfill",
        "Rights": "Outlines privileges and permissions granted to parties",
        "Termination": "Describes conditions and procedures for ending the agreement",
        "Confidentiality": "Addresses protection of sensitive information",
        "Payment Terms": "Specifies financial obligations and payment procedures",
        "Governing Law": "Establishes legal jurisdiction and applicable laws",
        "Liability": "Addresses responsibility for damages or losses",
        "Data Protection": "Covers handling and protection of personal information",
        "Intellectual Property": "Addresses ownership and use of IP assets",
        "Dispute Resolution": "Outlines procedures for resolving conflicts",
        "Force Majeure": "Addresses unforeseeable circumstances beyond control",
        "Miscellaneous": "General provisions that don't fit other categories"
    }
    
    return {
        "type": classification,
        "confidence": confidence,
        "explanation": explanations.get(classification, "General legal provision")
    }

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
    
    # Since we don't have transformers anymore, use simple text truncation
    # Take the first sentence and truncate to reasonable length
    sentences = text.split('.')
    if sentences:
        first_sentence = sentences[0].strip() + '.'
        if len(first_sentence) > 150:
            first_sentence = first_sentence[:147] + '...'
        return first_sentence
    else:
        return text[:150] + "..." if len(text) > 150 else text

# Extract dates and deadlines
def create_meaningful_context(date_text: str, sentence: str) -> str:
    """Create a clear, meaningful context that explains what the date is for (max 2 lines, complete sentences)"""
    sentence_lower = sentence.lower()
    
    # First, try to create a concise but complete context based on content type
    if 'submit' in sentence_lower or 'file' in sentence_lower:
        # Remove redundant "within" if date_text already contains it
        timeframe = date_text
        if 'within' in date_text.lower():
            timeframe = date_text
            prefix = ""
        else:
            prefix = "within "
        
        if 'report' in sentence_lower:
            base = f"Reports must be submitted {prefix}{timeframe}."
        elif 'invoice' in sentence_lower:
            base = f"Invoice must be submitted {prefix}{timeframe}."
        elif 'documentation' in sentence_lower:
            base = f"Documentation must be submitted {prefix}{timeframe}."
        else:
            base = f"Documents must be submitted {prefix}{timeframe}."
        
        # Add completion details if space allows
        if 'after completion' in sentence_lower and len(base) < 60:
            return f"{base} Required after completion of deliverables."
        elif 'after acceptance' in sentence_lower and len(base) < 60:
            return f"{base} Required after acceptance of work."
        return base
    
    elif 'notice' in sentence_lower or 'notify' in sentence_lower:
        if 'terminate' in sentence_lower:
            return f"Termination requires {date_text} written notice. Either party may terminate with proper notice."
        elif 'cancel' in sentence_lower:
            return f"Cancellation requires {date_text} prior written notice. Policy cannot be canceled without notice."
        else:
            return f"Written notice period: {date_text}. Required for breach notification."
    
    elif 'remedy' in sentence_lower or 'cure' in sentence_lower or 'correct' in sentence_lower:
        return f"Breach cure period: {date_text}. CONSULTANT must remedy violations within this timeframe."
    
    elif 'pay' in sentence_lower or 'payment' in sentence_lower:
        return f"Payment deadline: {date_text}. All deductibles and retentions must be paid within this period."
    
    elif 'coverage' in sentence_lower or 'insurance' in sentence_lower:
        return f"Insurance coverage period: {date_text}. Required coverage after agreement expiration."
    
    elif 'retain' in sentence_lower or 'maintain' in sentence_lower:
        if 'record' in sentence_lower:
            return f"Record retention period: {date_text}. Records must be maintained from final payment date."
        else:
            return f"Retention period: {date_text}. Documents must be kept for this duration."
    
    elif 'inspect' in sentence_lower or 'review' in sentence_lower:
        return f"Inspection frequency: {date_text}. CONSULTANT shall perform reviews on this basis."
    
    elif 'address' in sentence_lower:
        return f"Address reference: {date_text}"
    
    elif 'code' in sentence_lower or 'division' in sentence_lower:
        return f"Legal code reference: {date_text}"
    
    elif 'page' in sentence_lower:
        return f"Document page reference: {date_text}"
    
    else:
        # Extract meaningful context by finding complete sentence fragments
        # Split the sentence and find the part containing the date
        sentence_parts = re.split(r'[.!?]', sentence)
        
        # Find the part containing our date
        date_part = ""
        for part in sentence_parts:
            if date_text.lower() in part.lower():
                date_part = part.strip()
                break
        
        if date_part:
            # If the part is reasonably short, use it as is
            if len(date_part) <= 100:
                return date_part + "."
            
            # Otherwise, extract around the date but ensure complete words
            words = date_part.split()
            date_words = date_text.split()
            
            # Find date position
            date_word_start = -1
            for i, word in enumerate(words):
                if date_words[0].lower() in word.lower():
                    date_word_start = i
                    break
            
            if date_word_start != -1:
                # Extract context ensuring we don't cut mid-sentence
                # Look for sentence beginning markers
                start_idx = 0
                for i in range(date_word_start - 1, -1, -1):
                    if words[i].lower() in ['must', 'shall', 'will', 'the', 'all', 'within', 'after', 'before']:
                        start_idx = i
                        break
                
                # Find reasonable end point
                end_idx = min(len(words), date_word_start + len(date_words) + 8)
                
                # Extract and ensure it's not too long
                context = ' '.join(words[start_idx:end_idx])
                if len(context) <= 100:
                    return context + "."
                
                # If still too long, use minimal context around date
                start_idx = max(0, date_word_start - 3)
                end_idx = min(len(words), date_word_start + len(date_words) + 3)
                return ' '.join(words[start_idx:end_idx]) + "."
        
        # Final fallback: use the original sentence but ensure it's complete
        if len(sentence) <= 120:
            return sentence if sentence.endswith('.') else sentence + "."
        
        # If sentence is too long, extract a meaningful portion
        return sentence[:100].rsplit(' ', 1)[0] + "..."

def extract_dates(text: str, nlp) -> List[Dict[str, str]]:
    """Extract important dates with context from text"""
    if not nlp:
        # Fallback regex-based extraction if no NLP model
        return extract_dates_fallback(text)
    
    doc = nlp(text)
    dates = []
    
    for ent in doc.ents:
        if ent.label_ == "DATE":
            # Get the sentence containing the date
            sent = ent.sent
            sentence_text = sent.text.strip()
            
            # Extract better context by including neighboring sentences for complete context
            date_text = ent.text
            
            # Get the current sentence and try to get neighboring sentences for fuller context
            sentences = list(doc.sents)
            current_sent_idx = -1
            
            # Find the index of the current sentence
            for i, s in enumerate(sentences):
                if s.start <= ent.start < s.end:
                    current_sent_idx = i
                    break
            
            if current_sent_idx != -1:
                # Create meaningful context that explains what the date is for
                context = create_meaningful_context(date_text, sentence_text)
            else:
                context = sentence_text
            
            # Clean up context
            context = re.sub(r'\s+', ' ', context).strip()
            
            # Create meaningful description
            description = create_date_description(date_text, sentence_text)
            
            dates.append({
                'date': ent.text,
                'context': context,
                'description': description,
                'full_sentence': sentence_text,
                'category': categorize_date(date_text, sentence_text)
            })
    
    return dates

def extract_dates_fallback(text: str) -> List[Dict[str, str]]:
    """Fallback date extraction using regex when NLP model is not available"""
    import re

    # Enhanced date patterns to capture more comprehensive date references
    date_patterns = [
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # Date formats like 12/31/2023
        r'\b\d+\s+calendar\s+days?\b',  # calendar days
        r'\b\d+[-–]\s*calendar\s+days?\b',  # 45-calendar days
        r'\bno late[r]? than \d+\s*calendar\s+days?\b',
        r'\bwithin \d+[-–]\s*calendar\s+days?\b',
        r'\b(?:thirty|ten|five|three|sixty|ninety)[-–]?\s*days?\b',  # Written numbers with days
        r'\bthirty[-–]\s*day\b',
        r'\b\d{1,2}\s+years?\s+(?:old|after|from|period)\b',  # years with context
        r'\b(?:within|up to|at least|no later than)\s+\d+\s+days?\b',
        r'\b(?:within|up to|at least|no later than)\s+\d+\s+(?:work\s+)?days?\b',
        r'\b\d+\s+months?\s+(?:after|before|from|period)\b',  # months with context
        r'\bbetween the ages? of \d+\b',
        r'\bages? \d+ (?:and|to) \d+\b',
        r'\banother \d+\s+days?\b',
        r'\bperiod of \d+\s+(?:days?|months?|years?)\b',  # period specifications
        r'\bfor \d+\s+(?:days?|months?|years?)\s+(?:after|from|period)\b',
        r'\b\d+\s+(?:work\s+)?days?\s+(?:after|before|prior)\b'  # days with temporal context
    ]
    
    dates = []
    # Split by periods and other sentence endings for better sentence detection
    sentences = re.split(r'[.!?]+', text)
    
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_text = match.group()
            match_start = match.start()
            match_end = match.end()
            
            # Find which sentence contains this date by position
            best_sentence = ""
            sentence_start = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                sentence_end = sentence_start + len(sentence)
                
                # Check if the match falls within this sentence
                if sentence_start <= match_start <= sentence_end:
                    best_sentence = sentence
                    break
                
                sentence_start = text.find(sentence, sentence_start) + len(sentence)
            
            if not best_sentence:
                # Fallback: find sentence containing the date text
                for sentence in sentences:
                    if date_text.lower() in sentence.lower():
                        best_sentence = sentence.strip()
                        break
            
            if best_sentence:
                # Create meaningful context that explains what the date is for
                context = create_meaningful_context(date_text, best_sentence)
                context = re.sub(r'\s+', ' ', context).strip()
                
                description = create_date_description(date_text, best_sentence)
                
                # Check for duplicates before adding
                is_duplicate = False
                for existing_date in dates:
                    if existing_date['date'].lower() == date_text.lower() and existing_date['context'].lower() == context.lower():
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    dates.append({
                        'date': date_text,
                        'context': context,
                        'description': description,
                        'full_sentence': best_sentence,
                        'category': categorize_date(date_text, best_sentence)
                    })
    
    return dates

def create_date_description(date_text: str, sentence: str) -> str:
    """Create a meaningful description for the date based on context"""
    date_lower = date_text.lower()
    sentence_lower = sentence.lower()
    
    # Age requirements
    if 'years old' in date_lower or ('age' in sentence_lower and 'years' in date_lower):
        if 'under' in sentence_lower or 'less than' in sentence_lower:
            return f"Maximum age requirement: {date_text}"
        elif 'over' in sentence_lower or 'at least' in sentence_lower:
            return f"Minimum age requirement: {date_text}"
        elif 'between' in sentence_lower:
            return f"Age range: {date_text}"
        else:
            return f"Age requirement: {date_text}"
    
    # Deadlines and submission requirements
    elif 'no later than' in sentence_lower or 'deadline' in sentence_lower:
        return f"Submission deadline: {date_text}"
    elif 'within' in sentence_lower and ('submit' in sentence_lower or 'file' in sentence_lower or 'provide' in sentence_lower):
        return f"Submission deadline: {date_text}"
    
    # Notice periods
    elif 'notice' in sentence_lower or 'notify' in sentence_lower:
        return f"Notice requirement: {date_text}"
    
    # Time periods and deadlines
    elif 'days' in date_lower or 'day' in date_lower:
        if 'terminate' in sentence_lower or 'cancel' in sentence_lower:
            return f"Termination notice period: {date_text}"
        elif 'remedy' in sentence_lower or 'cure' in sentence_lower or 'correct' in sentence_lower:
            return f"Cure period: {date_text}"
        elif 'pay' in sentence_lower or 'payment' in sentence_lower:
            return f"Payment deadline: {date_text}"
        elif 'delete' in sentence_lower or 'removal' in sentence_lower:
            return f"Deletion timeframe: {date_text}"
        elif 'within' in sentence_lower:
            return f"Compliance deadline: {date_text}"
        elif 'up to' in sentence_lower:
            return f"Maximum duration: {date_text}"
        else:
            return f"Time period: {date_text}"
    
    # Months/Years
    elif 'month' in date_lower or 'year' in date_lower:
        if 'retain' in sentence_lower or 'keep' in sentence_lower or 'maintain' in sentence_lower:
            return f"Retention period: {date_text}"
        elif 'coverage' in sentence_lower or 'insurance' in sentence_lower:
            return f"Coverage period: {date_text}"
        elif 'period' in sentence_lower:
            return f"Duration period: {date_text}"
        else:
            return f"Time duration: {date_text}"
    
    # Calendar days specifically
    elif 'calendar' in sentence_lower:
        if 'submit' in sentence_lower or 'file' in sentence_lower:
            return f"Submission deadline: {date_text}"
        else:
            return f"Statutory timeframe: {date_text}"
    
    else:
        return f"Important timeframe: {date_text}"

def categorize_date(date_text: str, sentence: str) -> str:
    """Categorize the date into meaningful groups"""
    date_lower = date_text.lower()
    sentence_lower = sentence.lower()
    
    if 'years old' in date_lower or ('age' in sentence_lower and 'years' in date_lower):
        return "Age Requirements"
    elif 'submit' in sentence_lower or 'file' in sentence_lower or 'no later than' in sentence_lower:
        return "Submission Deadlines"
    elif 'notice' in sentence_lower or 'notify' in sentence_lower:
        return "Notice Requirements"
    elif 'terminate' in sentence_lower or 'cancel' in sentence_lower:
        return "Termination Periods"
    elif 'remedy' in sentence_lower or 'cure' in sentence_lower or 'correct' in sentence_lower:
        return "Cure Periods"
    elif 'pay' in sentence_lower or 'payment' in sentence_lower:
        return "Payment Deadlines"
    elif 'coverage' in sentence_lower or 'insurance' in sentence_lower:
        return "Insurance Periods"
    elif 'retain' in sentence_lower or 'keep' in sentence_lower or 'maintain' in sentence_lower:
        return "Retention Periods"
    elif 'delete' in sentence_lower or 'remove' in sentence_lower:
        return "Deletion Timeframes"
    elif 'calendar' in sentence_lower:
        return "Statutory Timeframes"
    elif 'within' in sentence_lower or 'deadline' in sentence_lower:
        return "Compliance Deadlines"
    else:
        return "General Timeframes"

# Extract document title and type
def extract_document_info(text: str, nlp) -> Dict[str, str]:
    """Extract document title, type and purpose from the beginning of the document"""
    # Take first few paragraphs for analysis
    first_part = text[:1000]
    doc = nlp(first_part)
    
    # Common legal document patterns
    doc_type_patterns = {
        'Terms of Service': r'terms?\s+of\s+(service|use)',
        'Privacy Policy': r'privacy\s+policy',
        'License Agreement': r'license\s+agreement',
        'Service Agreement': r'service\s+agreement', 
        'Terms and Conditions': r'terms?\s+and\s+conditions',
        'User Agreement': r'user\s+agreement',
        'Contract': r'contract|agreement',
        'Policy': r'policy'
    }
    
    document_type = "Legal Document"  # Default
    document_title = ""
    
    # Look for document type in first few sentences
    first_sentences = [sent.text for sent in list(doc.sents)[:5]]
    combined_text = ' '.join(first_sentences).lower()
    
    for doc_type, pattern in doc_type_patterns.items():
        if re.search(pattern, combined_text, re.IGNORECASE):
            document_type = doc_type
            break
    
    # Try to extract title (often the first meaningful sentence or heading)
    lines = text.split('\n')[:10]  # First 10 lines
    for line in lines:
        line = line.strip()
        if len(line) > 10 and len(line) < 200:  # Reasonable title length
            # Check if it looks like a title (not too long, has key terms)
            if any(term in line.lower() for term in ['terms', 'policy', 'agreement', 'service', 'privacy']):
                document_title = line
                break
    
    # If no title found, create one based on type and content
    if not document_title:
        # Look for organization names
        org_names = []
        for ent in doc.ents:
            if ent.label_ == "ORG" and len(ent.text) > 2:
                org_names.append(ent.text)
        
        if org_names:
            document_title = f"{org_names[0]} {document_type}"
        else:
            document_title = document_type
    
    return {
        'title': document_title,
        'type': document_type,
        'purpose': f"This document outlines the {document_type.lower()} governing the relationship between the parties."
    }

# Enhanced formatting functions
def format_document_analysis(document_info: Dict, clauses_analysis: List[Dict], 
                            dates_with_context: List[Dict]) -> str:
    """Format the complete document analysis in a professional, readable format"""
    
    output = []
    
    # Document Header
    output.append("=" * 80)
    output.append("LEGAL DOCUMENT ANALYSIS REPORT")
    output.append("=" * 80)
    output.append("")
    
    # Document Information
    output.append("DOCUMENT OVERVIEW")
    output.append("-" * 40)
    output.append(f"Title: {document_info['title']}")
    output.append(f"Document Type: {document_info['type']}")
    output.append(f"Purpose: {document_info['purpose']}")
    output.append("")
    
    # Clauses Analysis
    if clauses_analysis:
        output.append("CLAUSE-BY-CLAUSE ANALYSIS")
        output.append("-" * 40)
        
        for i, clause in enumerate(clauses_analysis, 1):
            output.append(f"\n{i}. {clause.get('title', f'Section {i}')}")
            output.append(f"   Type: {clause.get('classification', {}).get('type', 'Unknown')}")
            output.append(f"   Confidence: {clause.get('classification', {}).get('confidence', 'Low')}")
            output.append(f"   Explanation: {clause.get('classification', {}).get('explanation', 'N/A')}")
            
            if clause.get('summary'):
                output.append(f"   Summary: {clause['summary']}")
            
            if clause.get('important_points'):
                output.append("   Key Points:")
                for point in clause['important_points'][:3]:  # Top 3 points
                    output.append(f"   • {point}")
            
            if clause.get('obligations'):
                output.append("   Obligations:")
                for party, obligations in clause['obligations'].items():
                    if obligations:
                        output.append(f"   - {party}:")
                        for obligation in obligations[:2]:  # Top 2 obligations
                            output.append(f"     • {obligation}")
    
    # Important Dates Section
    if dates_with_context:
        output.append("\n\nIMPORTANT DATES AND DEADLINES")
        output.append("-" * 40)
        
        # Group dates by category for better organization
        categories = {}
        for date_info in dates_with_context:
            category = date_info.get('category', 'General Timeframes')
            if category not in categories:
                categories[category] = []
            categories[category].append(date_info)
        
        for category, dates in categories.items():
            if dates:
                output.append(f"\n{category}:")
                for date_info in dates:
                    description = date_info.get('description', date_info['date'])
                    context = date_info.get('context', '')
                    
                    if description and description != date_info['date']:
                        output.append(f"• {description}")
                        if context:
                            output.append(f"  Context: {context}")
                    else:
                        output.append(f"• {date_info['date']}: {context}")
    
    output.append("\n" + "=" * 80)
    output.append("END OF ANALYSIS REPORT")
    output.append("=" * 80)
    
    return "\n".join(output)

def format_dates_section(dates_with_context: List[Dict]) -> str:
    """Format dates section with clear context and better categorization"""
    if not dates_with_context:
        return "No specific dates found in the document."
    
    output = []
    output.append("IMPORTANT DATES AND TIMEFRAMES")
    output.append("=" * 50)
    
    # Use the enhanced categorization
    date_categories = {
        'Age Requirements': [],
        'Notice Periods': [],
        'Deletion/Removal Timeframes': [],
        'Deadlines': [],
        'Retention Periods': [],
        'General Timeframes': []
    }
    
    for date_info in dates_with_context:
        category = date_info.get('category', 'General Timeframes')
        if category not in date_categories:
            category = 'General Timeframes'
        date_categories[category].append(date_info)
    
    for category, dates in date_categories.items():
        if dates:
            output.append(f"\n{category}:")
            output.append("-" * len(category))
            for date_info in dates:
                description = date_info.get('description', date_info['date'])
                context = date_info.get('context', '')
                
                # Format the output more professionally
                if description and description != date_info['date']:
                    output.append(f"• {description}")
                    if context and len(context) > 20:
                        output.append(f"  Context: {context}")
                else:
                    output.append(f"• {date_info['date']}: {context}")
                
                # Add full sentence if it provides additional clarity
                if 'full_sentence' in date_info and len(date_info['full_sentence']) < 150:
                    full_sent = date_info['full_sentence'].strip()
                    if full_sent and full_sent != context:
                        output.append(f"  Full context: {full_sent}")
    
    return "\n".join(output)

def format_obligations_section(all_obligations: Dict[str, List[str]]) -> str:
    """Format obligations in a clear, structured way"""
    if not all_obligations:
        return "No specific obligations identified."
    
    output = []
    output.append("PARTY OBLIGATIONS")
    output.append("=" * 30)
    
    for party, obligations in all_obligations.items():
        if obligations:
            output.append(f"\n{party}:")
            output.append("-" * len(party))
            for i, obligation in enumerate(obligations, 1):
                # Clean up the obligation text
                clean_obligation = re.sub(r'\s+', ' ', obligation).strip()
                output.append(f"{i}. {clean_obligation}")
    
    return "\n".join(output)

def create_executive_summary(document_info: Dict, clauses_analysis: List[Dict], 
                           dates_with_context: List[Dict], all_obligations: Dict) -> str:
    """Create a concise executive summary of the document"""
    
    output = []
    output.append("EXECUTIVE SUMMARY")
    output.append("=" * 30)
    output.append("")
    
    # Document overview
    output.append(f"This {document_info['type'].lower()} titled '{document_info['title']}' ")
    output.append(f"contains {len(clauses_analysis)} main sections covering various legal provisions.")
    output.append("")
    
    # Key clause types
    clause_types = {}
    for clause in clauses_analysis:
        clause_type = clause.get('classification', {}).get('type', 'Unknown')
        clause_types[clause_type] = clause_types.get(clause_type, 0) + 1
    
    if clause_types:
        output.append("Key Areas Covered:")
        for clause_type, count in sorted(clause_types.items()):
            output.append(f"• {clause_type} ({count} section{'s' if count > 1 else ''})")
        output.append("")
    
    # Important dates summary
    if dates_with_context:
        output.append(f"The document references {len(dates_with_context)} important dates/timeframes,")
        output.append("including age requirements, notice periods, and deadlines.")
        output.append("")
    
    # Obligations summary
    if all_obligations:
        total_obligations = sum(len(obligations) for obligations in all_obligations.values())
        output.append(f"Total of {total_obligations} specific obligations identified across ")
        output.append(f"{len(all_obligations)} parties/categories.")
    
    return "\n".join(output)
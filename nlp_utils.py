import re
from collections import defaultdict
from typing import Dict, List, Any, List, Optional
import spacy

import PyPDF2


# Document preprocessing
def preprocess_text(text: str, lang: str = "en") -> str:
    """Clean and normalize document text"""
    if lang == "bn":
        # Bengali-specific cleaning
        text = re.sub(r'\s+', ' ', text).strip()  # Remove excessive whitespace
        text = re.sub(r'[\u0964\u0965]', ' ', text)  # Replace Bengali full stops (।, ॥)
        return text
    else:
        # English cleaning
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\[.*?\]', '', text)  # Remove citations like [1]
        text = re.sub(r'\(.*?\)', '', text)  # Remove text in parentheses
        return text

# Extract text from PDF
def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text content from PDF files"""
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return preprocess_text(text)

# Clause segmentation
def segment_clauses(doc: str, lang: str = "en") -> List[tuple]:
    """Split document into logical clauses/sections"""
    clauses = []
    current_clause = ""
    
    if lang == "en":
        patterns = [
            r'(?:\d+\.\s+[A-Z]{2,})',          # Match numbered clauses like "1. DUTIES" or "2. COMPENSATION"
            r'(?:Article\s+\d+\.\s+[A-Z]{2,})', # Match "Article X. TITLE"
            r'(?:SECTION\s+\d+\.\s+[A-Z]{2,})', # Match "SECTION X. TITLE"
            r'(?:\([a-z]\)\s+[A-Z]{2,})',       # Match sub-clauses like "(a) TITLE"
            r'(?:WHEREAS\s+[A-Z]{2,})'          # Match preamble-like "WHEREAS TITLE"
        ]
    elif lang == "bn":
        patterns = [
            r'(?:অধ্যায়\s+\d+[.:]\s+[অ-য়]{2,})',      # Match "অধ্যায় X. TITLE" (Chapter X)
            r'(?:ধারা\s+\d+[.:]\s+[অ-য়]{2,})',         # Match "ধারা X. TITLE" (Section X)
            r'(?:অনুচ্ছেদ\s+\d+[.:]\s+[অ-য়]{2,})',      # Match "অনুচ্ছেদ X. TITLE" (Article X)
            r'(?:\([১-৯]\)\s+[অ-য়]{2,})',              # Match sub-clauses like "(১) TITLE"
            r'(?:যেহেতু\s+[অ-য়]{2,})'                  # Match preamble-like "যেহেতু TITLE" (WHEREAS equivalent)
        ]
    else:
        return clauses  # Return empty list for unsupported languages

    split_regex = re.compile('|'.join(patterns))
    parts = split_regex.split(doc)
    matches = split_regex.findall(doc)
    
    if len(parts) > 1:
        # First part as preamble if it doesn’t match a numbered clause
        preamble_text = parts[0].strip()
        if preamble_text and not any(m in preamble_text for m in matches):
            clauses.append(("Preamble", preamble_text))
        
        for i in range(1, len(parts)):
            clause_title = matches[i-1].strip() if i <= len(matches) else f"Clause {i}" if lang == "en" else f"অনুচ্ছেদ {i}"
            clause_content = parts[i].strip()
            if clause_content:  # Only add if content exists
                clauses.append((clause_title, clause_content))
    else:
        # Fallback: split by double newlines or paragraphs
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', doc) if p.strip()]
        for i, para in enumerate(paragraphs):
            if lang == "en":
                match = re.match(r'(\d+)\.\s+([A-Za-z].*)', para)
                if match:
                    clause_title = f"{match.group(1)}. {match.group(2)}"
                    content = re.sub(r'^\d+\.\s+[A-Za-z].*\n?', '', para).strip()
                    clauses.append((clause_title, content))
                else:
                    clauses.append((f"Paragraph {i+1}", para))
            elif lang == "bn":
                match = re.match(r'(অধ্যায়|ধারা|অনুচ্ছেদ)\s+(\d+)\.\s+([অ-য়].*)', para)
                if match:
                    clause_title = f"{match.group(1)} {match.group(2)}. {match.group(3)}"
                    content = re.sub(r'^(অধ্যায়|ধারা|অনুচ্ছেদ)\s+\d+\.\s+[অ-য়].*\n?', '', para).strip()
                    clauses.append((clause_title, content))
                else:
                    clauses.append((f"অনুচ্ছেদ {i+1}", para))
    
    return clauses
# Classify clause type
def classify_clause(text: str, tokenizer=None, model=None, lang: str = "en") -> Dict[str, str]:
    """Classify the type of legal clause using both ML and rule-based approaches"""
    
    clause_keywords = {
        "en": {
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
        },
        "bn": {
            "সংজ্ঞা": ["সংজ্ঞা", "বোঝায়", "অর্থ", "নির্ধারিত", "উল্লেখ"],  # Definitions
            "বাধ্যবাধকতা": ["বাধ্য", "কর্তব্য", "দায়িত্ব", "আবশ্যক"],  # Obligations
            "অধিকার": ["অধিকার", "অনুমোদিত", "প্রাপ্য"],  # Rights
            "সমাপ্তি": ["সমাপ্তি", "বাতিল", "শেষ"],  # Termination
            "গোপনীয়তা": ["গোপনীয়", "গোপন", "সুরক্ষিত"],  # Confidentiality
            "বিবিধ": []  # Miscellaneous
        }
    }
    
    text_lower = text.lower() if lang == "en" else text
    keywords = clause_keywords.get(lang, clause_keywords["en"])
    scores = {}
    
    # Calculate scores for each category
    for category, kw_list in keywords.items():
        score = sum(1 for keyword in kw_list if keyword in text_lower)
        if kw_list:
            scores[category] = score
    
    # Get best match
    if scores:
        best_category = max(scores.items(), key=lambda x: x[1])
        classification = best_category[0] if best_category[1] > 0 else ("Miscellaneous" if lang == "en" else "বিবিধ")
    else:
        classification = "Miscellaneous" if lang == "en" else "বিবিধ"
    
    # If model is available, use it for additional insight
    confidence = "Medium"
    if tokenizer and model:
        try:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = model(**inputs)
            predicted_class = outputs.logits.argmax().item()
            
            class_mapping = {
                "en": {
                    0: "Definitions", 1: "Obligations", 2: "Rights", 3: "Termination",
                    4: "Confidentiality", 5: "Payment Terms", 6: "Governing Law",
                    7: "Liability", 8: "Data Protection", 9: "Miscellaneous"
                },
                "bn": {
                    0: "সংজ্ঞা", 1: "বাধ্যবাধকতা", 2: "অধিকার", 3: "সমাপ্তি",
                    4: "গোপনীয়তা", 5: "পেমেন্ট শর্তাবলী", 6: "শাসন আইন",
                    7: "দায়বদ্ধতা", 8: "তথ্য সুরক্ষা", 9: "বিবিধ"
                }
            }
            
            ml_classification = class_mapping.get(lang, class_mapping["en"]).get(predicted_class, "Miscellaneous" if lang == "en" else "বিবিধ")
            
            # Use ML result if it matches rule-based or if rule-based is uncertain
            if ml_classification == classification or classification == ("Miscellaneous" if lang == "en" else "বিবিধ"):
                classification = ml_classification
                confidence = "High"
                
        except Exception as e:
            print(f"ML classification failed: {e}")
    
    # Add explanation
    explanations = {
        "en": {
            "Definitions": "Contains definitions of terms used throughout the document",
            "Obligations": "Specifies duties and requirements that parties must fulfill",
            "Rights": "Outlines privileges and permissions granted to parties",
            "Termination": "Describes conditions and procedures for ending the agreement",
            "Confidentiality": "Addresses protection of sensitive information",
            "Payment Terms": "Specifies financial obligations and payment conditions",
            "Governing Law": "Defines the legal jurisdiction and applicable laws",
            "Liability": "Outlines responsibilities for damages or losses",
            "Data Protection": "Addresses handling of personal or sensitive data",
            "Intellectual Property": "Covers ownership and use of intellectual assets",
            "Dispute Resolution": "Describes methods for resolving conflicts",
            "Force Majeure": "Covers exemptions due to unforeseen circumstances",
            "Miscellaneous": "Other provisions not classified elsewhere"
        },
        "bn": {
            "সংজ্ঞা": "দলিলে ব্যবহৃত শব্দের সংজ্ঞা রয়েছে",
            "বাধ্যবাধকতা": "পক্ষগুলির পূরণ করতে হবে এমন দায়িত্ব এবং প্রয়োজনীয়তা নির্দিষ্ট করে",
            "অধিকার": "পক্ষগুলির জন্য প্রদত্ত বিশেষাধিকার এবং অনুমতি বর্ণনা করে",
            "সমাপ্তি": "চুক্তি শেষ করার শর্ত এবং পদ্ধতি বর্ণনা করে",
            "গোপনীয়তা": "সংবেদনশীল তথ্যের সুরক্ষা বিষয়ে আলোচনা করে",
            "বিবিধ": "অন্যান্য শ্রেণীবদ্ধ না হওয়া বিষয়বস্তু"
        }
    }
    
    return {
        "type": classification,
        "confidence": confidence,
        "explanation": explanations.get(lang, explanations["en"]).get(classification, "")
    }

# Extract document information
def extract_document_info(text: str, nlp) -> Dict[str, str]:
    """Extract basic document information using NLP"""
    doc = nlp(text[:1000])  # Process first 1000 chars to keep it fast
    
    title = "Legal Document"
    doc_type = "Legal Document"
    purpose = "N/A"
    
    # Simple heuristic for title (first line or sentence)
    first_line = text.split('\n')[0].strip()
    if len(first_line) > 10 and len(first_line) < 100:
        title = first_line
    
    # Look for common document types
    doc_types = {
        "Agreement": ["agreement", "contract", "deal"],
        "Policy": ["policy", "terms", "conditions"],
        "Notice": ["notice", "notification"],
        "Deed": ["deed", "title"]
    }
    
    text_lower = text.lower()
    for dtype, keywords in doc_types.items():
        if any(keyword in text_lower for keyword in keywords):
            doc_type = dtype
            break
    
    # Extract purpose (basic heuristic)
    purpose_keywords = ["purpose", "objective", "intent"]
    for sent in doc.sents:
        if any(keyword in sent.text.lower() for keyword in purpose_keywords):
            purpose = sent.text.strip()
            break
    
    return {
        "title": title,
        "type": doc_type,
        "purpose": purpose
    }

# Extract important points

def extract_important_points(text: str, nlp: Optional[spacy.language.Language] = None, 
                           bnlp_ner=None, lang: str = "en") -> List[str]:
    """
    Extract key points from a clause or document section.
    
    Args:
        text (str): The text to analyze.
        nlp (Optional[spacy.language.Language]): SpaCy model for English processing (None for Bengali).
        bnlp_ner: Bengali NER model for entity extraction (None if not available).
        lang (str): Language code ("en" for English, "bn" for Bengali).
    
    Returns:
        List[str]: List of up to 5 extracted key points.
    """
    points = []

    if lang == "en" and nlp:
        # English processing with spaCy
        doc = nlp(text)
        obligation_keywords = ["shall", "must", "require", "agree", "obligate", "ensure"]
        
        for sent in doc.sents:
            # Check for sentences with key entities or obligation keywords
            has_entities = any(ent.label_ in ["PERSON", "ORG", "DATE", "GPE"] for ent in sent.ents)
            has_obligation = any(token.lemma_.lower() in obligation_keywords for token in sent)
            has_strong_structure = any(token.dep_ in ["ROOT", "nsubj"] and token.pos_ in ["VERB", "NOUN"] for token in sent)
            
            if has_entities or has_obligation or has_strong_structure:
                points.append(sent.text.strip())

    elif lang == "bn":
        # Bengali processing
        sentences = [s.strip() for s in re.split(r'[\u0964\n]', text) if s.strip()]
        obligation_keywords = ["বাধ্য", "কর্তব্য", "দায়িত্ব", "আবশ্যক", "নিশ্চিত"]

        for sent in sentences:
            # Check for obligation keywords
            has_obligation = any(keyword in sent for keyword in obligation_keywords)
            
            # Check for entities using bnlp_ner if available
            has_entities = False
            if bnlp_ner:
                try:
                    entities = bnlp_ner(sent)  # Assuming bnlp_ner returns list of (text, label) tuples
                    has_entities = any(label in ["PERSON", "ORGANIZATION", "DATE"] for _, label in entities)
                except Exception as e:
                    print(f"Error using bnlp_ner: {e}")

            if has_obligation or has_entities:
                points.append(sent)

    # Deduplicate and limit to 5 points
    points = list(dict.fromkeys(points))[:5]
    return points if points else ["No key points identified."]

# Extract dates
import re
from typing import List, Dict, Any

def extract_dates(text: str, nlp: Any = None, lang: str = "en") -> List[Dict]:
    """
    Extract dates and timeframes from text, filtering out garbage like ZIP codes, street numbers, or section references.
    Supports English and Bengali.
    """
    dates = []
    
    if lang == "en":
        # Timeframe patterns (e.g., "monthly", "45 calendar days", "within 60 days")
        timeframe_patterns = [
            r'\b(monthly|weekly|daily|annually|quarterly|biannually|semi-annually)\b',  # Frequency words
            r'\b(\d+[\s-]*(?:calendar[\s-]*)?(?:days?|months?|years?|weeks?|hours?))\b',  # "45 days", "60-calendar days"
            r'\b(within|no later than|later than|no less than|no more than|after|before|upon|from|until|by)\s+(\d+[\s-]*(?:calendar[\s-]*)?(?:days?|months?|years?|weeks?|hours?))\b',  # Contextual timeframes
        ]
        
        for pattern in timeframe_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_str = match.group(0).strip()
                # Get surrounding context
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = re.sub(r'\s+', ' ', text[start:end]).strip()
                
                # Skip if context looks like an address or section reference
                if re.search(r'\b(ave|avenue|st|street|rd|road|blvd|boulevard|ca|ny|tx|zip|address|pacific|cruz|division|section|article|chapter)\b', context.lower(), re.IGNORECASE):
                    continue
                
                # Skip ZIP-like 5-digit numbers or standalone numbers in lists (e.g., "11, 12, 13")
                if re.match(r'^\d{1,5}$', date_str) or re.search(r'\b\d+\s*,\s*\d+\b', context):
                    continue
                
                dates.append({
                    "date": date_str,
                    "context": context,
                    "full_sentence": context,
                    "category": "Timeframe"
                })
        
        # Specific date patterns (e.g., "10/18/2025", "October 18, 2025")
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',  # MM/DD/YYYY or MM/DD/YY
            r'\b(\d{1,2} (?:january|february|march|april|may|june|july|august|september|october|november|december) \d{2,4})\b',  # DD Month YYYY
            r'\b((?:january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2},? \d{2,4})\b',  # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_str = match.group(0).strip()
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = re.sub(r'\s+', ' ', text[start:end]).strip()
                
                # Skip address-like contexts, section references, or ZIPs
                if re.search(r'\b(ave|avenue|st|street|rd|road|blvd|boulevard|ca|ny|tx|zip|address|pacific|cruz|division|section|article|chapter)\b', context.lower(), re.IGNORECASE) or re.match(r'^\d{5}$', date_str):
                    continue
                
                dates.append({
                    "date": date_str,
                    "context": context,
                    "full_sentence": context,
                    "category": "Specific Date"
                })
        
        # Enhance with spaCy DATE entities if nlp is available
        if nlp:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ == "DATE":
                    date_str = ent.text.strip()
                    context = re.sub(r'\s+', ' ', ent.sent.text).strip()
                    
                    # Skip garbage: ZIP-like, address contexts, section references, or standalone numbers
                    if (re.match(r'^\d{1,5}$', date_str) or 
                        re.search(r'\b(ave|avenue|st|street|rd|road|blvd|boulevard|ca|ny|tx|zip|address|pacific|cruz|division|section|article|chapter)\b', context.lower(), re.IGNORECASE) or 
                        re.search(r'\b\d+\s*,\s*\d+\b', context)):
                        continue
                    
                    dates.append({
                        "date": date_str,
                        "context": context,
                        "full_sentence": context,
                        "category": "Date"
                    })
    
    elif lang == "bn":
        # Bengali timeframe patterns (equivalent to English)
        timeframe_patterns = [
            r'\b(মাসিক|সাপ্তাহিক|দৈনিক|বার্ষিক|ত্রৈমাসিক|অর্ধ-বার্ষিক)\b',  # Frequency words
            r'\b(\d+[\s-]*(?:ক্যালেন্ডার[\s-]*)?(?:দিন|মাস|বছর|সপ্তাহ|ঘন্টা))\b',  # "৪৫ দিন"
            r'\b(মধ্যে|পরে না|পরে|কম না|বেশি না|পর|পূর্বে|উপর|থেকে|পর্যন্ত|দ্বারা)\s+(\d+[\s-]*(?:ক্যালেন্ডার[\s-]*)?(?:দিন|মাস|বছর|সপ্তাহ|ঘন্টা))\b',  # Contextual timeframes
        ]
        
        for pattern in timeframe_patterns:
            for match in re.finditer(pattern, text):
                date_str = match.group(0).strip()
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = re.sub(r'\s+', ' ', text[start:end]).strip()
                
                # Skip address-like contexts or section references (Bengali equivalents)
                if re.search(r'\b(এভি|অ্যাভিনিউ|স্ট|স্ট্রিট|আরডি|রোড|বিএলভিডি|বুলেভার্ড|সিএ|এনওয়াই|টিএক্স|জিপ|ঠিকানা|অধ্যায়|ধারা|অনুচ্ছেদ)\b', context):
                    continue
                
                # Skip ZIP-like 5-digit numbers or numbers in lists
                if re.match(r'^\d{5}$', date_str) or re.search(r'\b\d+\s*,\s*\d+\b', context):
                    continue
                
                dates.append({
                    "date": date_str,
                    "context": context,
                    "full_sentence": context,
                    "category": "Timeframe"
                })
        
        # Add Bengali-specific date patterns (e.g., "১৮ অক্টোবর ২০২৫")
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',  # Numeric format: ১৮/১০/২০২৫
            r'\b(\d{1,2} (?:জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|অগাস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর) \d{2,4})\b',  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            for match in re.finditer(pattern, text):
                date_str = match.group(0).strip()
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = re.sub(r'\s+', ' ', text[start:end]).strip()
                
                # Skip address or section contexts
                if re.search(r'\b(এভি|অ্যাভিনিউ|স্ট|স্ট্রিট|আরডি|রোড|বিএলভিডি|বুলেভার্ড|সিএ|এনওয়াই|টিএক্স|জিপ|ঠিকানা|অধ্যায়|ধারা|অনুচ্ছেদ)\b', context):
                    continue
                
                dates.append({
                    "date": date_str,
                    "context": context,
                    "full_sentence": context,
                    "category": "Specific Date"
                })
    
    # Deduplicate based on date + partial context
    unique_dates = []
    seen = set()
    for d in dates:
        key = d["date"] + d["context"][:30]
        if key not in seen:
            unique_dates.append(d)
            seen.add(key)
    
    return unique_dates

# Extract obligations
def extract_obligations(text: str, nlp=None, lang: str = "en") -> Dict[str, List[str]]:
    """Extract obligations for different parties"""
    obligations = defaultdict(list)
    
    if lang == "bn":
        obligation_patterns = [
            r'(?:পক্ষ|দল)\s*([^।]*?)\s*(করতে\s*হবে|দায়িত্ব|বাধ্য)\s*([^।]*)',
            r'(?:[^।]*?)\s*(প্রদান\s*করতে|অনুমোদন\s*করতে)\s*([^।]*)',
        ]
        for pattern in re.finditer('|'.join(obligation_patterns), text):
            party = "Party"  # Placeholder; improve with NER
            obligation = re.sub(r'\s+', ' ', pattern.group(0)).strip()
            obligations[party].append(obligation)
    else:
        obligation_patterns = [
            r'(?:party|parties)\s*(.*?)\s*(?:shall|must|required to)\s*(.*?)(?:\.|$)',
            r'(?:[^.]*?)\s*(?:agrees to|undertakes to)\s*([^.]*?)(?:\.|$)',
        ]
        for pattern in re.finditer('|'.join(obligation_patterns), text, re.IGNORECASE):
            party = "Party"  # Placeholder; improve with NER
            obligation = re.sub(r'\s+', ' ', pattern.group(0)).strip()
            obligations[party].append(obligation)
    
    # Use NLP for party identification
    if nlp:
        doc = nlp(text[:2000])  # Limit for performance
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG"]:
                for sent in doc.sents:
                    if ent.text in sent.text and any(keyword in sent.text.lower() for keyword in ["shall", "must", "required", "করতে হবে", "দায়িত্ব"]):
                        obligations[ent.text].append(sent.text.strip())
    
    return dict(obligations)

# Summarize clause
def summarize_clause(text: str, summarizer, lang: str = "en") -> str:
    """Generate a summary for a clause with proper truncation."""
    if not summarizer:
        return "Summary not available (no summarizer loaded)"
    try:
        # Truncate input to fit model's max token length (1024 for mbart-large-50)
        max_input_tokens = 1000  # Slightly below 1024 to be safe
        inputs = summarizer.tokenizer(text, truncation=True, max_length=max_input_tokens, return_tensors="pt")
        input_token_count = inputs['input_ids'].shape[1]
        
        # Set max_length for summary (shorter than input) and adjust min_length
        max_len = min(input_token_count // 2, 100)  # Aim for ~50% of input or 100 tokens
        min_len = max(10, max_len // 2)  # Ensure min_length is reasonable
        
        # Generate summary
        summary = summarizer(
            text,
            max_length=max_len,
            min_length=min_len,
            do_sample=False,
            truncation=True
        )[0]['summary_text']
        return summary
    except Exception as e:
        return f"Error summarizing clause: {str(e)}"

# Format document analysis
def format_document_analysis(document_info: Dict, clauses_analysis: List[Dict], 
                           dates_with_context: List[Dict], summarizer=None) -> Dict[str, Any]:
    """Format the full document analysis into a professional report"""
    output = []
    output.append("=" * 80)
    output.append("LEGAL DOCUMENT ANALYSIS REPORT")
    output.append("=" * 80)
    output.append("")

    # Document Overview
    output.append("DOCUMENT OVERVIEW")
    output.append("=" * 30)
    output.append(f"Title: {document_info.get('title', 'N/A')}")
    output.append(f"Type: {document_info.get('type', 'N/A')}")
    output.append(f"Purpose: {document_info.get('purpose', 'N/A')}")
    output.append("")

    # Clause Analysis
    output.append("CLAUSE ANALYSIS")
    output.append("=" * 30)

    for clause in clauses_analysis:
        output.append(f"\n{clause['title']}:")
        output.append("-" * len(clause['title']))

        classification = clause.get('classification', {})
        clause_type = classification.get('type', 'Unknown')
        confidence = classification.get('confidence', 'N/A')
        explanation = classification.get('explanation', '')

        output.append(f"Classification: {clause_type} (Confidence: {confidence})")
        if explanation:
            output.append(f"Explanation: {explanation}")
        output.append(f"Summary: {clause.get('summary', 'N/A')}")

        if clause.get("important_points"):
            output.append("Key Points:")
            for point in clause["important_points"]:
                output.append(f"• {point}")

        if clause.get("obligations"):
            output.append("Obligations:")
            for party, obligations in clause["obligations"].items():
                output.append(f"  {party}:")
                for obl in obligations:
                    output.append(f"    • {obl}")

        if clause.get("dates"):
            output.append("Important Dates:")
            for date_info in clause["dates"]:
                output.append(f"• {date_info['date']}: {date_info['context']}")

    # Important Dates Section
    if dates_with_context:
        output.append("\n" + format_dates_section(dates_with_context))

    # Obligations Summary
    all_obligations = {}
    for clause in clauses_analysis:
        for party, obligations in clause.get("obligations", {}).items():
            if party not in all_obligations:
                all_obligations[party] = []
            all_obligations[party].extend(obligations)

    if all_obligations:
        output.append("\n" + format_obligations_section(all_obligations))

    output.append("\n" + "=" * 80)
    output.append("END OF ANALYSIS REPORT")
    output.append("=" * 80)

    # Create a basic summary (e.g., using create_executive_summary)
    basic_summary = create_executive_summary(document_info, clauses_analysis, dates_with_context, all_obligations)

    # Return a dictionary instead of a string
    return {
        "is_basic": False,  # Set to True if you want to generate only a basic summary in some cases
        "full_report": "\n".join(output),
        "basic_summary": basic_summary
    }

# Format dates section
def format_dates_section(dates_with_context: List[Dict]) -> str:
    """Format dates section with clear context and better categorization"""
    if not dates_with_context:
        return "No specific dates found in the document."
    
    output = []
    output.append("IMPORTANT DATES AND TIMEFRAMES")
    output.append("=" * 50)
    
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
                
                if description and description != date_info['date']:
                    output.append(f"• {description}")
                    if context and len(context) > 20:
                        output.append(f"  Context: {context}")
                else:
                    output.append(f"• {date_info['date']}: {context}")
                
                if 'full_sentence' in date_info and len(date_info['full_sentence']) < 150:
                    full_sent = date_info['full_sentence'].strip()
                    if full_sent and full_sent != context:
                        output.append(f"  Full context: {full_sent}")
    
    return "\n".join(output)

# Format obligations section
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
                clean_obligation = re.sub(r'\s+', ' ', obligation).strip()
                output.append(f"{i}. {clean_obligation}")
    
    return "\n".join(output)

# Create executive summary
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

from firebase_setup import db
import time
import re
from collections import Counter

def generate_analysis_name(analysis):
    """
    Generate an intelligent name based on document content analysis
    """
    # Extract basic info
    clauses = analysis.get("clauses", [])
    
    # If no clauses, fallback to simple naming
    if not clauses:
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        return f"Document_Analysis_{timestamp}"
    
    # Analyze clause types to identify document category
    clause_types = [clause.get("type", "Unknown") for clause in clauses]
    type_counter = Counter(clause_types)
    
    # Determine document type based on clause patterns
    document_type = identify_document_type(type_counter, clauses)
    
    # Extract key entities or parties
    parties = extract_parties_from_clauses(clauses)
    
    # Extract key subject matter
    subject_matter = extract_subject_matter(clauses)
    
    # Build intelligent name
    name_parts = []
    
    # Add document type
    if document_type and document_type != "Legal_Document":
        name_parts.append(document_type)
    
    # Add subject matter if found
    if subject_matter:
        name_parts.append(subject_matter)
    
    # Add parties if identified
    if parties and len(parties) <= 2:
        party_str = "_".join(parties)
        name_parts.append(party_str)
    
    # If we couldn't determine much, use dominant clause type
    if not name_parts:
        dominant_type = type_counter.most_common(1)[0][0] if type_counter else "Document"
        name_parts.append(dominant_type.replace(" ", "_"))
    
    # Add clause count for context
    name_parts.append(f"{len(clauses)}clauses")
    
    # Add timestamp
    timestamp = time.strftime("%Y%m%d_%H%M", time.localtime())
    
    # Combine parts (limit total length)
    base_name = "_".join(name_parts)[:50]  # Limit length
    return f"{base_name}_{timestamp}"

def identify_document_type(type_counter, clauses):
    """
    Identify document type based on clause patterns and content
    """
    # Check clause titles and content for document type indicators
    all_text = " ".join([
        clause.get("title", "") + " " + 
        clause.get("summary", "") + " " + 
        clause.get("full_text", "")[:200]  # First 200 chars
        for clause in clauses
    ]).lower()
    
    # Document type patterns
    patterns = {
        "Service_Agreement": ["service", "services", "performance", "deliverable"],
        "Employment_Contract": ["employment", "employee", "employer", "salary", "termination"],
        "Non_Disclosure_Agreement": ["confidential", "non-disclosure", "nda", "proprietary"],
        "Purchase_Agreement": ["purchase", "sale", "buyer", "seller", "goods"],
        "License_Agreement": ["license", "intellectual property", "copyright", "patent"],
        "Lease_Agreement": ["lease", "rental", "tenant", "landlord", "property"],
        "Partnership_Agreement": ["partnership", "partner", "joint venture", "collaboration"],
        "Software_Agreement": ["software", "application", "code", "system", "platform"],
        "Terms_of_Service": ["terms of service", "user agreement", "platform", "website"],
        "Privacy_Policy": ["privacy", "data protection", "personal information", "cookies"],
        "Consulting_Agreement": ["consulting", "consultant", "advisory", "professional services"]
    }
    
    # Score each document type
    scores = {}
    for doc_type, keywords in patterns.items():
        score = sum(all_text.count(keyword) for keyword in keywords)
        if score > 0:
            scores[doc_type] = score
    
    # Return the highest scoring type
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    # Fallback to clause type analysis
    dominant_types = type_counter.most_common(3)
    if dominant_types:
        dominant = dominant_types[0][0]
        if "Payment" in dominant:
            return "Financial_Agreement"
        elif "Confidentiality" in dominant:
            return "NDA"
        elif "Obligations" in dominant:
            return "Service_Contract"
        elif "Rights" in dominant:
            return "Rights_Agreement"
    
    return "Legal_Document"

def extract_parties_from_clauses(clauses):
    """
    Extract party names or organizations from clauses
    """
    parties = set()
    
    for clause in clauses:
        # Check obligations section for parties
        obligations = clause.get("obligations", {})
        for party in obligations.keys():
            if party != "All Parties":
                # Clean and add party name
                clean_party = re.sub(r'[^a-zA-Z0-9]', '', party)[:15]  # Clean and limit length
                if len(clean_party) > 2:  # Avoid short artifacts
                    parties.add(clean_party)
        
        # Extract from clause text using simple patterns
        text = clause.get("full_text", "") + " " + clause.get("summary", "")
        
        # Look for company/organization patterns
        company_patterns = [
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:Inc|LLC|Corp|Ltd|Company)\b',
            r'\b([A-Z][a-zA-Z]+)\s+(?:Inc|LLC|Corp|Ltd)\b'
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                clean_match = re.sub(r'[^a-zA-Z0-9]', '', match)[:15]
                if len(clean_match) > 2:
                    parties.add(clean_match)
    
    return list(parties)[:3]  # Return up to 3 parties

def extract_subject_matter(clauses):
    """
    Extract key subject matter or purpose from document
    """
    # Combine summaries to find common themes
    summaries = " ".join([clause.get("summary", "") for clause in clauses]).lower()
    
    # Key subject matter patterns
    subjects = {
        "Data_Processing": ["data", "processing", "information", "database"],
        "Software_Dev": ["software", "development", "application", "system"],
        "Marketing": ["marketing", "advertising", "promotion", "campaign"],
        "Research": ["research", "study", "analysis", "investigation"],
        "Consulting": ["consulting", "advisory", "professional", "expertise"],
        "Training": ["training", "education", "learning", "instruction"],
        "Maintenance": ["maintenance", "support", "service", "repair"],
        "Supply": ["supply", "delivery", "goods", "materials"],
        "Real_Estate": ["property", "real estate", "building", "premises"],
        "Financial": ["payment", "financial", "money", "compensation"]
    }
    
    scores = {}
    for subject, keywords in subjects.items():
        score = sum(summaries.count(keyword) for keyword in keywords)
        if score > 0:
            scores[subject] = score
    
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    return None

def save_analysis(user, analysis):
    # Get user ID with fallback
    user_id = user.get('localId')
    if not user_id:
        # Fallback: use email as identifier (not ideal but functional)
        user_id = user.get('email', 'unknown_user')
    
    token = user['idToken']
    name = generate_analysis_name(analysis)
    db.child("analyses").child(user_id).child(name).set({
        "name": name,
        "timestamp": int(time.time()),
        "analysis": analysis
    }, token)

def get_saved_analyses(user):
    # Get user ID with fallback
    user_id = user.get('localId')
    if not user_id:
        # Fallback: use email as identifier (not ideal but functional)
        user_id = user.get('email', 'unknown_user')
    
    analyses = db.child("analyses").child(user_id).get()
    if analyses.each():
        return [item.val() for item in analyses.each()]
    return []
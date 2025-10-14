import spacy
import streamlit as st
import sys
import os

# Load models (do this once at startup)
@st.cache_resource
def load_models():
    # SpaCy for basic NLP (this is all we have now without transformers)
    try:
        # Try multiple ways to load the model
        nlp = None
        
        # First try: load by name
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Second try: load by full package name
            try:
                import en_core_web_sm
                nlp = en_core_web_sm.load()
            except ImportError:
                # Third try: reinstall and load
                st.warning("SpaCy model not found. Attempting to install...")
                import subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", "en-core-web-sm", "--find-links", "https://github.com/explosion/spacy-models/releases"], check=True)
                nlp = spacy.load("en_core_web_sm")
        
        if nlp is None:
            raise OSError("Could not load SpaCy model")
            
    except Exception as e:
        st.error(f"SpaCy English model not found. Error: {str(e)}")
        st.error("Please install it with: python -m spacy download en_core_web_sm")
        st.info("Or try: pip install en-core-web-sm --find-links https://github.com/explosion/spacy-models/releases")
        st.stop()
    
    # Return None for the transformer models that are no longer available
    classifier_tokenizer = None
    classifier_model = None
    summarizer = None
    ner_pipeline = None
    
    return nlp, classifier_tokenizer, classifier_model, summarizer, ner_pipeline
import tokenize
import spacy
import streamlit as st
import sys
import os
from bnlp import BasicTokenizer, BengaliNER
import torch
from transformers import pipeline

# Load models (do this once at startup)
@st.cache_resource
def load_models():
    # Load English spaCy model
    try:
        # Try multiple ways to load the model
        nlp_en = None
        
        # First try: load by name
        try:
            nlp_en = spacy.load("en_core_web_sm")
        except OSError:
            # Second try: load by full package name
            try:
                import en_core_web_sm
                nlp_en = en_core_web_sm.load()
            except ImportError:
                # Third try: reinstall and load
                st.warning("SpaCy model not found. Attempting to install...")
                import subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", "en-core-web-sm", "--find-links", "https://github.com/explosion/spacy-models/releases"], check=True)
                nlp_en = spacy.load("en_core_web_sm")
        
        if nlp_en is None:
            raise OSError("Could not load SpaCy model")
            
    except Exception as e:
        st.error(f"SpaCy English model not found. Error: {str(e)}")
        st.error("Please install it with: python -m spacy download en_core_web_sm")
        st.info("Or try: pip install en-core-web-sm --find-links https://github.com/explosion/spacy-models/releases")
        st.stop()
    
    # Load Bengali NLP tools
    try:
        bnlp_tokenizer = BasicTokenizer()
        bnlp_ner = BengaliNER()
    except Exception as e:
        st.error(f"Failed to load Bengali NLP tools: {str(e)}")
        st.error("Please install bnlp_toolkit with: pip install bnlp_toolkit")
        st.stop()
    
    # Load multilingual summarizer (optional, can be None if not needed)
    try:
        device = 0 if torch.cuda.is_available() else -1
        summarizer = pipeline("summarization", model="csebuetnlp/mT5_multilingual_XLSum", tokenizer="csebuetnlp/mT5_multilingual_XLSum", device=device)
    except Exception as e:
        st.warning(f"Failed to load summarizer: {str(e)}. Summarization will be disabled.")
        summarizer = None
    
    # Placeholder for transformer-based classifier models (not used currently)
    classifier_tokenizer = None
    classifier_model = None
    ner_pipeline = None
    
    return nlp_en, bnlp_tokenizer, bnlp_ner, classifier_tokenizer, classifier_model, summarizer, ner_pipeline
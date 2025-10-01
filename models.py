import spacy
import streamlit as st

# Load models (do this once at startup)
@st.cache_resource
def load_models():
    # SpaCy for basic NLP (this is all we have now without transformers)
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        st.error("SpaCy English model not found. Please install it with: python -m spacy download en_core_web_sm")
        st.stop()
    
    # Return None for the transformer models that are no longer available
    classifier_tokenizer = None
    classifier_model = None
    summarizer = None
    ner_pipeline = None
    
    return nlp, classifier_tokenizer, classifier_model, summarizer, ner_pipeline
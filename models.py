import spacy
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import streamlit as st

# Load models (do this once at startup)
@st.cache_resource
def load_models():
    # SpaCy for basic NLP
    nlp = spacy.load("en_core_web_lg")
    
    # Legal BERT for clause classification
    classifier_tokenizer = AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased")
    classifier_model = AutoModelForSequenceClassification.from_pretrained("nlpaueb/legal-bert-base-uncased")
    
    # Summarization pipeline
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    
    # NER for legal entities
    ner_pipeline = pipeline("ner", model="dslim/bert-base-NER")
    
    return nlp, classifier_tokenizer, classifier_model, summarizer, ner_pipeline
import time
from typing import Any, Dict
import streamlit as st
from langdetect import detect
from auth import load_session, login, logout, register
from models import load_models
from nlp_utils import (
    classify_clause, create_executive_summary, extract_dates,
    extract_document_info, extract_important_points, extract_obligations,
    format_dates_section, format_document_analysis, format_obligations_section,
    preprocess_text, segment_clauses, summarize_clause
)
from pdf_utils import extract_text_from_pdf
from save_analysis import get_saved_analyses, save_analysis, delete_analysis
from datetime import datetime

# ---------------- Load user session on reload ---------------- #
load_session()

def analyze_bengali_document(text: str, bnlp_tokenizer, bnlp_ner) -> Dict[str, Any]:
    """Analyze Bengali legal document using bnlp_toolkit"""
    text = preprocess_text(text, lang="bn")
    
    doc_info = {
        "document_info": {"title": "Unknown", "type": "Legal Document", "purpose": "N/A"},
        "metadata": {"length": len(text), "estimated_clauses": 0},
        "clauses": [],
        "all_dates": [],
        "all_obligations": {}
    }
    
    clauses = segment_clauses(text, lang="bn")
    for title, clause_text in clauses:
        if not clause_text.strip() or len(clause_text.split()) < 5:
            continue
        try:
            # Enhanced classification with explanations
            classification = classify_clause(clause_text, lang="bn")
            important_points = extract_important_points(clause_text, None, lang="bn")
            obligations = extract_obligations(clause_text, bnlp_ner, lang="bn")
            summary = summarize_clause(clause_text, None, lang="bn")
            dates = extract_dates(clause_text, bnlp_ner, lang="bn")

            # Collect all dates and obligations
            doc_info["all_dates"].extend(dates)
            for party, party_obligations in obligations.items():
                if party not in doc_info["all_obligations"]:
                    doc_info["all_obligations"][party] = []
                doc_info["all_obligations"][party].extend(party_obligations)

            doc_info["clauses"].append({
                "title": title,
                "classification": classification,
                "summary": summary,
                "important_points": important_points,
                "obligations": obligations,
                "dates": dates,
                "full_text": clause_text[:1000]
            })
        except Exception as e:
            print(f"Error processing clause {title}: {e}")
            continue
    
    doc_info["metadata"]["estimated_clauses"] = len(doc_info["clauses"])
    return doc_info

def analyze_document(text: str, models, lang: str = "en") -> Dict[str, Any]:
    nlp_en, bnlp_tokenizer, bnlp_ner, classifier_tokenizer, classifier_model, summarizer, ner_pipeline = models
    
    detected_lang = lang
    if lang == "auto":
        try:
            detected_lang = detect(text[:1000])
        except:
            detected_lang = "en"
    
    if detected_lang == "bn":
        return analyze_bengali_document(text, bnlp_tokenizer, bnlp_ner)
    else:
        text = preprocess_text(text, lang="en")
        document_info = extract_document_info(text, nlp_en)
        
        doc_info = {
            "document_info": document_info,
            "metadata": {
                "length": len(text),
                "estimated_clauses": text.count("SECTION") + text.count("Article") + 1
            },
            "clauses": [],
            "all_dates": [],
            "all_obligations": {}
        }
        
        clauses = segment_clauses(text, lang="en")
        print(f"Debug: Number of clauses detected: {len(clauses)}")  # Debug output
        for title, clause_text in clauses:
            if not clause_text.strip() or len(clause_text.split()) < 5:
                continue
            try:
                classification = classify_clause(clause_text, classifier_tokenizer, classifier_model, lang="en")
                important_points = extract_important_points(clause_text, nlp_en, lang="en")
                obligations = extract_obligations(clause_text, nlp_en, lang="en")
                summary = summarize_clause(clause_text, summarizer, lang="en")
                dates = extract_dates(clause_text, nlp_en, lang="en")

                doc_info["all_dates"].extend(dates)
                for party, party_obligations in obligations.items():
                    if party not in doc_info["all_obligations"]:
                        doc_info["all_obligations"][party] = []
                    doc_info["all_obligations"][party].extend(party_obligations)

                doc_info["clauses"].append({
                    "title": title,
                    "classification": classification,
                    "summary": summary,
                    "important_points": important_points,
                    "obligations": obligations,
                    "dates": dates,
                    "full_text": clause_text[:1000]
                })
            except Exception as e:
                print(f"Error processing clause {title}: {e}")
                continue
        
        doc_info["metadata"]["estimated_clauses"] = len(doc_info["clauses"])
        return doc_info

# ---------------- Streamlit UI ---------------- #
def main_app():
    st.title("Legal Document Analyzer")
    st.write("Upload a legal document (PDF or text) to analyze its contents")

    # Language selector
    lang = st.selectbox("Select Language", ["Auto", "English", "Bengali"], key="lang_select")
    lang_code = "bn" if lang == "Bengali" else "en" if lang == "English" else "auto"

    models = load_models()
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
        else:
            text = uploaded_file.read().decode("utf-8")


        with st.spinner("Analyzing document..."):
            analysis = analyze_document(text, models, lang=lang_code)

        st.success("Analysis complete!")

        st.subheader("Document Overview")
        
        # Display document information if available
        if "document_info" in analysis:
            doc_info = analysis["document_info"]
            st.write(f"**Document Title**: {doc_info['title']}")
            st.write(f"**Document Type**: {doc_info['type']}")
            st.write(f"**Purpose**: {doc_info['purpose']}")
            st.write("---")
        
        st.write(f"**Length**: {analysis['metadata']['length']} characters")
        st.write(f"**Number of clauses**: {len(analysis['clauses'])}")

        # Show enhanced dates section if available
        if "all_dates" in analysis and analysis["all_dates"]:
            st.subheader("Important Dates & Deadlines")
            for date_info in analysis["all_dates"]:
                if isinstance(date_info, dict):
                    st.write(f"📅 **{date_info['date']}**: {date_info['context']}")
                else:
                    st.write(f"📅 {date_info}")

        st.subheader("Clause Breakdown")
        for clause in analysis["clauses"]:
            clause_type = "Unknown"
            if isinstance(clause.get('classification'), dict):
                clause_type = clause['classification'].get('type', 'Unknown')
                confidence = clause['classification'].get('confidence', 'Low')
                explanation = clause['classification'].get('explanation', '')
            elif 'type' in clause:
                clause_type = clause['type']
                confidence = "N/A"
                explanation = ""
            
            with st.expander(f"{clause['title']} - {clause_type}"):
                if isinstance(clause.get('classification'), dict):
                    st.write(f"**Classification**: {clause_type} (Confidence: {confidence})")
                    if explanation:
                        st.write(f"**Explanation**: {explanation}")
                
                st.write(f"**Summary**: {clause['summary']}")

                if clause["important_points"]:
                    st.write("**Important Points**:")
                    for point in clause["important_points"]:
                        st.write(f"- {point}")

                if clause["obligations"]:
                    st.write("**Obligations**:")
                    for party, obligations in clause["obligations"].items():
                        st.write(f"*{party}*:")
                        for obl in obligations:
                            st.write(f"  - {obl}")

                if clause["dates"]:
                    st.write("**Important Dates in this Clause**:")
                    for date in clause["dates"]:
                        if isinstance(date, dict):
                            st.write(f"- **{date['date']}**: {date['context']}")
                        else:
                            st.write(f"- {date}")

        # Generate and display report
        report_data = format_document_analysis(
            analysis["document_info"],
            analysis["clauses"],
            analysis["all_dates"],
            models[5]
        )
        col1, col2 = st.columns(2)
        with col1:
            if report_data.get("is_basic"):
                st.download_button(
                    label="📥 Download Basic Report",
                    data=report_data["basic_summary"],
                    file_name="legal_document_basic_analysis.txt",
                    mime="text/plain",
                    key="download_basic_btn"
                )
            else:
                st.download_button(
                    label="📥 Download Report as Text File",
                    data=report_data["full_report"],
                    file_name="legal_document_analysis.txt",
                    mime="text/plain",
                    key="download_full_btn"
                )
            
        with col2:
            if st.session_state.get("user"):
                save_key = "save_basic_report_stored" if report_data.get("is_basic") else "save_comprehensive_report_stored"
                save_label = "💾 Save Basic Report" if report_data.get("is_basic") else "💾 Save Report to My Account"
                
                if st.button(save_label, key=save_key):
                    print(f"Attempting to save {'basic' if report_data.get('is_basic') else 'comprehensive'} report...")
                    try:
                        save_analysis(
                            st.session_state["user"],
                            analysis,
                            report_data["basic_summary"] if report_data.get("is_basic") else report_data["full_report"]
                        )
                        st.success("✅ Report saved to your account!")
                    except Exception as e:
                        print(f"Error saving report: {e}")
                        st.error(f"❌ Error saving report: {e}")
            else:
                st.info("🔒 Login to save reports to your account")

def sidebar_auth():
    st.sidebar.title("Navigation")

    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"

    if st.session_state.get("user"):
        st.sidebar.success(f"✅ Logged in: {st.session_state['user'].get('email', 'Unknown')}")
    else:
        st.sidebar.info("❌ Not logged in")

    menu_options = ["Analyze Document"]
    if not st.session_state["user"]:
        menu_options.append("Login/Register")
    else:
        menu_options.append("See Saved Files")

    page = st.sidebar.radio("Go to", menu_options, key="main_menu")

    if page == "Login/Register":
        if st.session_state["user"]:
            user_email = st.session_state["user"].get("email", "Unknown")
            st.sidebar.success(f"Logged in as: {user_email}")
        else:
            if st.session_state["auth_mode"] == "login":
                login()
                if st.button("Go to Register"):
                    st.session_state["auth_mode"] = "register"
                    st.rerun()
            elif st.session_state["auth_mode"] == "register":
                register()
                if st.button("Go to Login"):
                    st.session_state["auth_mode"] = "login"
                    st.rerun()

    elif page == "See Saved Files":
        user_email = st.session_state["user"].get("email", "Unknown")
        saved = get_saved_analyses(st.session_state["user"])
        st.header("📁 Your Saved Analysis Reports")
        
        if saved:
            st.subheader("Filters")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=None)
            with col2:
                end_date = st.date_input("End Date", value=None)
            col3, col4 = st.columns(2)
            with col3:
                keyword = st.text_input("Keyword Search")
            with col4:
                unique_types = sorted(set(item.get("document_info", {}).get("type", "Unknown") for item in saved))
                doc_type = st.selectbox("Document Type", ["All"] + unique_types)

            filtered_saved = []
            for item in saved:
                date_match = True
                if 'timestamp' in item:
                    item_date = datetime.fromtimestamp(item["timestamp"])
                    if start_date:
                        date_match = date_match and (item_date.date() >= start_date)
                    if end_date:
                        date_match = date_match and (item_date.date() <= end_date)
                
                keyword_match = True
                if keyword:
                    search_text = ""
                    if 'name' in item:
                        search_text += item['name'] + " "
                    if 'document_info' in item:
                        search_text += item['document_info'].get('title', '') + " "
                    if 'final_report' in item:
                        search_text += item['final_report'] + " "
                    if 'basic_summary' in item:
                        search_text += item['basic_summary'] + " "
                    keyword_match = keyword.lower() in search_text.lower()
                
                type_match = True
                if doc_type != "All":
                    type_match = item.get("document_info", {}).get("type", "Unknown") == doc_type
                
                if date_match and keyword_match and type_match:
                    filtered_saved.append(item)

            # Sort by timestamp descending
            filtered_saved.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

            st.write(f"Found {len(filtered_saved)} saved report(s)")
            
            for idx, item in enumerate(filtered_saved, 1):
                display_name = item.get("name", f"Analysis {idx}")
                timestamp = item.get('timestamp')
                if timestamp and isinstance(timestamp, (int, float)):
                    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                else:
                    formatted_time = 'N/A'
                
                with st.expander(f"📄 {display_name} (Saved: {formatted_time})"):
                    doc_info = item.get("document_info", {})
                    if doc_info:
                        st.write(f"**Document Title:** {doc_info.get('title', 'N/A')}")
                        st.write(f"**Document Type:** {doc_info.get('type', 'N/A')}")
                        st.write(f"**Purpose:** {doc_info.get('purpose', 'N/A')}")
                    
                    summary = item.get("summary", {})
                    if summary:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Clauses", summary.get("total_clauses", 0))
                        with col2:
                            st.metric("Dates", summary.get("total_dates", 0))
                        with col3:
                            st.metric("Parties", summary.get("total_parties", 0))
                        with col4:
                            st.metric("Length", f"{summary.get('document_length', 0):,} chars")
                    
                    if item.get("final_report"):
                        st.subheader("📋 Final Analysis Report")
                        st.text_area("Report Content", item["final_report"], height=400, key=f"report_{idx}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 Download This Report",
                                data=item["final_report"],
                                file_name=f"{display_name}_report.txt",
                                mime="text/plain",
                                key=f"download_{idx}"
                            )
                        with col2:
                            if st.button("🗑️ Delete This Report", key=f"delete_{idx}"):
                                try:
                                    delete_analysis(st.session_state["user"], display_name)
                                    st.success(f"Report '{display_name}' deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting report: {e}")
                    elif item.get("basic_summary"):
                        st.subheader("📝 Analysis Summary")
                        st.text_area("Summary", item["basic_summary"], height=200, key=f"summary_{idx}")
                        if st.button("🗑️ Delete This Report", key=f"delete_{idx}"):
                            try:
                                delete_analysis(st.session_state["user"], display_name)
                                st.success(f"Report '{display_name}' deleted successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting report: {e}")
                    else:
                        st.warning("⚠️ No final report available for this analysis. This might be an older save format.")
                        if st.button("🗑️ Delete This Report", key=f"delete_{idx}"):
                            try:
                                delete_analysis(st.session_state["user"], display_name)
                                st.success(f"Report '{display_name}' deleted successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting report: {e}")
        else:
            st.info("📭 No saved reports found. Analyze a document and save the final report to see it here.")

    if st.session_state.get("user"):
        if st.sidebar.button("Logout", key="logout_btn"):
            logout()

    return page

def main():
    page = sidebar_auth()
    if page == "Analyze Document":
        main_app()

if __name__ == "__main__":
    main()
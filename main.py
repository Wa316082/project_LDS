import time
import streamlit as st
from typing import Dict, Any

from models import load_models
from nlp_utils import (
    preprocess_text, segment_clauses, classify_clause,
    extract_important_points, extract_obligations,
    summarize_clause, extract_dates, extract_document_info,
    format_document_analysis, format_dates_section, 
    format_obligations_section, create_executive_summary
)
from pdf_utils import extract_text_from_pdf
from auth import login, register, logout, load_session
from save_analysis import save_analysis, get_saved_analyses

# ---------------- Load user session on reload ---------------- #
load_session()

def analyze_document(text: str, models) -> Dict[str, Any]:
    nlp, classifier_tokenizer, classifier_model, summarizer, ner_pipeline = models
    text = preprocess_text(text)
    
    # Extract document information
    document_info = extract_document_info(text, nlp)
    
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
    
    clauses = segment_clauses(text)
    for title, clause_text in clauses:
        if not clause_text.strip() or len(clause_text.split()) < 5:
            continue
        try:
            # Enhanced classification with explanations
            classification = classify_clause(clause_text, classifier_tokenizer, classifier_model)
            important_points = extract_important_points(clause_text, nlp)
            obligations = extract_obligations(clause_text, nlp)
            summary = summarize_clause(clause_text, summarizer)
            dates = extract_dates(clause_text, nlp)

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
    return doc_info

# ---------------- Streamlit UI ---------------- #
def main_app():
    st.title("Legal Document Analyzer")
    st.write("Upload a legal document (PDF or text) to analyze its contents")

    models = load_models()
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
        else:
            text = uploaded_file.read().decode("utf-8")

        with st.spinner("Analyzing document..."):
            analysis = analyze_document(text, models)

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
            # Handle both old and new classification formats
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
                # Show classification details if available
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

                if st.checkbox(f"Show full text for {clause['title']}", key=clause["title"]):
                    st.text(clause["full_text"])

        # Enhanced summary sections
        if "all_obligations" in analysis and analysis["all_obligations"]:
            st.subheader("📋 All Party Obligations Summary")
            for party, obligations in analysis["all_obligations"].items():
                if obligations:
                    with st.expander(f"Obligations for {party}"):
                        for i, obligation in enumerate(obligations, 1):
                            st.write(f"{i}. {obligation}")

        # Professional report generation
        st.subheader("📄 Generate Professional Report")
        
        # Initialize session state for reports if not exists
        if "generated_reports" not in st.session_state:
            st.session_state["generated_reports"] = {}
        
        # Create a unique key for this analysis
        analysis_key = f"analysis_{hash(str(analysis))}"
        
        if st.button("Generate Comprehensive Report", key="generate_report_btn"):
            try:
                from nlp_utils import (
                    format_document_analysis, format_dates_section,
                    format_obligations_section, create_executive_summary
                )
                
                # Generate comprehensive report
                if "document_info" in analysis:
                    executive_summary = create_executive_summary(
                        analysis["document_info"], 
                        analysis["clauses"], 
                        analysis.get("all_dates", []), 
                        analysis.get("all_obligations", {})
                    )
                    
                    # Full formatted report
                    full_report = format_document_analysis(
                        analysis["document_info"],
                        analysis["clauses"], 
                        analysis.get("all_dates", [])
                    )
                    
                    # Store reports in session state
                    st.session_state["generated_reports"][analysis_key] = {
                        "executive_summary": executive_summary,
                        "full_report": full_report,
                        "analysis": analysis
                    }
                    
            except Exception as e:
                st.error(f"Error generating report: {e}")
                st.info("Using basic format instead")
                basic_report = f"""
Legal Document Analysis Report

Document Length: {analysis['metadata']['length']} characters
Number of Clauses: {len(analysis['clauses'])}

Clause Summary:
{chr(10).join([f"- {clause['title']}: {clause['summary'][:100]}..." for clause in analysis['clauses']])}
                """
                
                # Store basic report in session state
                st.session_state["generated_reports"][analysis_key] = {
                    "executive_summary": "Basic report generated due to error",
                    "full_report": basic_report,
                    "analysis": analysis,
                    "is_basic": True
                }
        
        # Display generated reports if they exist
        if analysis_key in st.session_state["generated_reports"]:
            report_data = st.session_state["generated_reports"][analysis_key]
            
            # Show executive summary
            st.text_area("Executive Summary", report_data["executive_summary"], height=200, key="exec_summary_display")
            
            # Show full report
            if report_data.get("is_basic"):
                st.text_area("Basic Report", report_data["full_report"], height=300, key="basic_report_display")
            else:
                st.text_area("Full Professional Report", report_data["full_report"], height=400, key="full_report_display")
            
            # Create columns for download and save buttons
            col1, col2 = st.columns(2)
            
            with col1:
                # Download button for report
                if report_data.get("is_basic"):
                    st.download_button(
                        label="📥 Download Basic Report",
                        data=report_data["full_report"],
                        file_name="basic_legal_analysis.txt",
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
                # Save button for logged-in users only
                if st.session_state.get("user"):
                    save_key = "save_basic_report_stored" if report_data.get("is_basic") else "save_comprehensive_report_stored"
                    save_label = "💾 Save Basic Report" if report_data.get("is_basic") else "💾 Save Report to My Account"
                    
                    if st.button(save_label, key=save_key):
                        print(f"Attempting to save {'basic' if report_data.get('is_basic') else 'comprehensive'} report...")
                        try:
                            save_analysis(st.session_state["user"], report_data["analysis"], report_data["full_report"])
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
            st.write(f"Found {len(saved)} saved report(s)")
            
            for idx, item in enumerate(saved, 1):
                display_name = item.get("name", f"Analysis {idx}")
                timestamp = item.get('timestamp')
                if timestamp and isinstance(timestamp, (int, float)):
                    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                else:
                    formatted_time = 'N/A'
                
                with st.expander(f"📄 {display_name} (Saved: {formatted_time})"):
                    
                    # Show document info
                    doc_info = item.get("document_info", {})
                    if doc_info:
                        st.write(f"**Document Title:** {doc_info.get('title', 'N/A')}")
                        st.write(f"**Document Type:** {doc_info.get('type', 'N/A')}")
                        st.write(f"**Purpose:** {doc_info.get('purpose', 'N/A')}")
                    
                    # Show summary statistics
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
                    
                    # Show the final report
                    if item.get("final_report"):
                        st.subheader("📋 Final Analysis Report")
                        st.text_area("Report Content", item["final_report"], height=400, key=f"report_{idx}")
                        
                        # Download button for saved report
                        st.download_button(
                            label="📥 Download This Report",
                            data=item["final_report"],
                            file_name=f"{display_name}_report.txt",
                            mime="text/plain",
                            key=f"download_{idx}"
                        )
                    elif item.get("basic_summary"):
                        st.subheader("📝 Analysis Summary")
                        st.text_area("Summary", item["basic_summary"], height=200, key=f"summary_{idx}")
                    else:
                        st.warning("⚠️ No final report available for this analysis. This might be an older save format.")
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

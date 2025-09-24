import time
import streamlit as st
from typing import Dict, Any

from models import load_models
from nlp_utils import (
    preprocess_text, segment_clauses, classify_clause,
    extract_important_points, extract_obligations,
    summarize_clause, extract_dates
)
from pdf_utils import extract_text_from_pdf
from auth import login, register, logout, load_session
from save_analysis import save_analysis, get_saved_analyses

# ---------------- Load user session on reload ---------------- #
load_session()

def analyze_document(text: str, models) -> Dict[str, Any]:
    nlp, classifier_tokenizer, classifier_model, summarizer, ner_pipeline = models
    text = preprocess_text(text)
    doc_info = {
        "metadata": {
            "length": len(text),
            "estimated_clauses": text.count("SECTION") + text.count("Article") + 1
        },
        "clauses": []
    }
    clauses = segment_clauses(text)
    for title, clause_text in clauses:
        if not clause_text.strip() or len(clause_text.split()) < 5:
            continue
        try:
            classification = classify_clause(clause_text, classifier_tokenizer, classifier_model)
            important_points = extract_important_points(clause_text, nlp)
            obligations = extract_obligations(clause_text, nlp)
            summary = summarize_clause(clause_text, summarizer)
            dates = extract_dates(clause_text, nlp)

            doc_info["clauses"].append({
                "title": title,
                "type": classification,
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
        st.write(f"Length: {analysis['metadata']['length']} characters")
        st.write(f"Number of clauses: {len(analysis['clauses'])}")

        st.subheader("Clause Breakdown")
        for clause in analysis["clauses"]:
            with st.expander(f"{clause['title']} - {clause['type']}"):
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
                    st.write("**Important Dates**:")
                    for date in clause["dates"]:
                        st.write(f"- {date}")

                if st.checkbox(f"Show full text for {clause['title']}", key=clause["title"]):
                    st.text(clause["full_text"])

                if st.session_state.get("user"):
                    if st.button("Save Analysis to My Account", key=f"save_{clause['title']}"):
                        save_analysis(st.session_state["user"], analysis)
                        st.success("Analysis saved to your account!")
                else:
                    st.info("Login to save your analysis.")


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
        st.header("Your Saved Analyses")
        if saved:
            for idx, item in enumerate(saved, 1):
                display_name = item.get("name", f"Analysis {idx}")
                timestamp = item.get('timestamp')
                if timestamp and isinstance(timestamp, (int, float)):
                    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                else:
                    formatted_time = 'N/A'
                st.markdown(f"---\n### {display_name} (Saved at {formatted_time})")
                analysis = item.get("analysis", {})

                if "metadata" in analysis:
                    st.write(f"**Length:** {analysis['metadata'].get('length', 'N/A')} characters")
                    st.write(f"**Number of clauses:** {len(analysis.get('clauses', []))}")

                st.subheader("Clause Breakdown")
                for clause in analysis.get("clauses", []):
                    with st.expander(f"{clause.get('title', 'Clause')} - {clause.get('type', 'Unknown')}"):
                        st.write(f"**Summary**: {clause.get('summary', '')}")

                        if clause.get("important_points"):
                            st.write("**Important Points**:")
                            for point in clause["important_points"]:
                                st.write(f"- {point}")

                        if clause.get("obligations"):
                            st.write("**Obligations**:")
                            for party, obligations in clause["obligations"].items():
                                st.write(f"*{party}*:")
                                for obl in obligations:
                                    st.write(f"  - {obl}")

                        if clause.get("dates"):
                            st.write("**Important Dates**:")
                            for date in clause["dates"]:
                                st.write(f"- {date}")

                        if st.checkbox(f"Show full text for {clause.get('title', 'Clause')}",
                                       key=f"saved_{idx}_{clause.get('title', str(idx))}"):
                            st.text(clause.get("full_text", ""))

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

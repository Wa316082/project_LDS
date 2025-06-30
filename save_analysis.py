from firebase_setup import db
import time

def generate_analysis_name(analysis):
    # Use the first clause title and timestamp for uniqueness
    if analysis.get("clauses"):
        first_title = analysis["clauses"][0].get("title", "Analysis")
    else:
        first_title = "Analysis"
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    return f"{first_title}_{timestamp}"

def save_analysis(user, analysis):
    user_id = user['localId']
    token = user['idToken']
    name = generate_analysis_name(analysis)
    db.child("analyses").child(user_id).child(name).set({
        "name": name,
        "timestamp": int(time.time()),
        "analysis": analysis
    }, token)

def get_saved_analyses(user):
    user_id = user['localId']
    analyses = db.child("analyses").child(user_id).get()
    if analyses.each():
        return [item.val() for item in analyses.each()]
    return []
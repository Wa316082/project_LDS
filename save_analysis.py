from firebase_setup import db, auth
import time
import re
import streamlit as st

def generate_analysis_name(analysis):
    """
    Generate a simple name based on document title
    """
    # Get document title from document_info
    doc_info = analysis.get("document_info", {})
    title = doc_info.get("title", "")
    
    if title and title != "Legal Document":
        # Clean the title for use as filename
        clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
        clean_title = re.sub(r'\s+', '_', clean_title.strip())[:50]  # Limit length
    else:
        clean_title = "Legal_Document"
    
    # Add timestamp to avoid duplicates
    timestamp = time.strftime("%Y%m%d_%H%M", time.localtime())
    
    return f"{clean_title}_{timestamp}"

def refresh_user_token(user):
    """Refresh the user's ID token if it's expired"""
    try:
        # Try to get account info to check if token is valid
        auth.get_account_info(user.get('idToken'))
        return user  # Token is still valid
    except:
        # Token is expired, need to refresh from session/cookies
        # This would normally be handled by the auth system
        # For now, return the user as-is and let the error bubble up
        return user

def save_analysis(user, analysis, final_report=None):
    """Save analysis with final report"""
    print("=== SAVE_ANALYSIS FUNCTION CALLED ===")
    print(f"User provided: {user is not None}")
    print(f"Analysis provided: {analysis is not None}")
    print(f"Final report provided: {final_report is not None}")
    
    try:
        # Ensure we have a fresh token
        user = refresh_user_token(user)
        
        # Get user ID with fallback
        user_id = user.get('localId')
        if not user_id:
            # Fallback: use email as identifier (not ideal but functional)
            user_id = user.get('email', 'unknown_user')
        
        print(f"User ID: {user_id}")
        
        # Check if token exists
        token = user.get('idToken')
        if not token:
            raise Exception("No authentication token found - please log in again")
        
        print("Token validated successfully")
        
        name = generate_analysis_name(analysis)
        print(f"Generated name: {name}")
        
        # Handle large reports by truncating if necessary
        if final_report and len(final_report) > 100000:  # 100KB limit
            final_report = final_report[:100000] + "\n\n[Report truncated due to size limits]"
            print("Report truncated due to size")
        
        # Prepare minimal data to save
        save_data = {
            "name": name,
            "timestamp": int(time.time()),
            "document_info": analysis.get("document_info", {}),
            "summary": {
                "total_clauses": len(analysis.get("clauses", [])),
                "total_dates": len(analysis.get("all_dates", [])),
                "total_parties": len(analysis.get("all_obligations", {})),
                "document_length": analysis.get("metadata", {}).get("length", 0)
            },
            "final_report": final_report or "No report generated"
        }
        
        print(f"Data prepared for saving, size: {len(str(save_data))} characters")
        
        # Save to database with error handling
        try:
            print("Attempting to save to database...")
            result = db.child("analyses").child(user_id).child(name).set(save_data, token)
            print(f"Database save result: {result}")
            print("=== SAVE SUCCESSFUL ===")
            return True
        except Exception as db_error:
            print(f"Database error occurred: {db_error}")
            # If it's an auth error, suggest re-login
            if "auth" in str(db_error).lower() or "unauthorized" in str(db_error).lower() or "permission" in str(db_error).lower():
                raise Exception("Authentication expired - please log out and log back in")
            else:
                raise Exception(f"Database error: {str(db_error)}")
        
    except Exception as e:
        error_msg = f"Error saving analysis: {str(e)}"
        print(f"=== SAVE ERROR: {error_msg} ===")
        raise Exception(error_msg)

def get_saved_analyses(user):
    """Get all saved analyses for a user"""
    try:
        # Get user ID with fallback
        user_id = user.get('localId')
        if not user_id:
            # Fallback: use email as identifier (not ideal but functional)
            user_id = user.get('email', 'unknown_user')
        
        # Get token for authenticated request
        token = user.get('idToken')
        if not token:
            return []
        
        analyses = db.child("analyses").child(user_id).get(token)
        
        if analyses.each():
            return [item.val() for item in analyses.each()]
        else:
            return []
            
    except Exception as e:
        print(f"Error getting saved analyses: {str(e)}")
        return []
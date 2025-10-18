from firebase_setup import db, auth
import time
import re
import streamlit as st
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_analysis_name(analysis):
    """
    Generate a simple name based on document title, supporting multilingual titles.
    """
    # Get document title from document_info
    doc_info = analysis.get("document_info", {})
    title = doc_info.get("title", "")
    
    if title and title != "Legal Document":
        # Clean the title for use as filename, preserving Bengali characters
        clean_title = re.sub(r'[^\w\s\u0980-\u09FF]', '', title)  # Allow Bengali Unicode
        clean_title = re.sub(r'\s+', '_', clean_title.strip())[:50]  # Limit length
    else:
        clean_title = "Legal_Document"
    
    # Add timestamp to avoid duplicates
    timestamp = time.strftime("%Y%m%d_%H%M", time.localtime())
    
    return f"{clean_title}_{timestamp}"

def refresh_user_token(user):
    """Refresh the user's ID token if it's expired."""
    try:
        # Try to get account info to check if token is valid
        auth.get_account_info(user.get('idToken'))
        logger.info("User token is valid")
        return user  # Token is still valid
    except Exception as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        # Token is expired, rely on session/cookies handled by auth.py
        return user

def save_analysis(user, analysis, final_report=None):
    """Save analysis with final report to Firebase."""
    logger.info("=== SAVE_ANALYSIS FUNCTION CALLED ===")
    logger.info(f"User provided: {user is not None}")
    logger.info(f"Analysis provided: {analysis is not None}")
    logger.info(f"Final report provided: {final_report is not None}")
    
    try:
        # Ensure we have a fresh token
        user = refresh_user_token(user)
        
        # Get user ID with fallback
        user_id = user.get('localId')
        if not user_id:
            user_id = user.get('email', 'unknown_user')
            logger.warning(f"No localId found, using email as fallback: {user_id}")
        
        logger.info(f"User ID: {user_id}")
        
        # Check if token exists
        token = user.get('idToken')
        if not token:
            raise Exception("No authentication token found - please log in again")
        
        logger.info("Token validated successfully")
        
        name = generate_analysis_name(analysis)
        logger.info(f"Generated name: {name}")
        
        # Handle large reports by truncating if necessary
        if final_report and len(final_report) > 100000:  # 100KB limit
            final_report = final_report[:100000] + "\n\n[Report truncated due to size limits]"
            logger.info("Report truncated due to size")
        
        # Prepare data to save
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
        
        logger.info(f"Data prepared for saving, size: {len(str(save_data))} characters")
        
        # Save to database with error handling
        try:
            logger.info("Attempting to save to database...")
            result = db.child("analyses").child(user_id).child(name).set(save_data, token)
            logger.info(f"Database save result: {result}")
            logger.info("=== SAVE SUCCESSFUL ===")
            return True
        except Exception as db_error:
            logger.error(f"Database error occurred: {str(db_error)}")
            if "auth" in str(db_error).lower() or "unauthorized" in str(db_error).lower() or "permission" in str(db_error).lower():
                raise Exception("Authentication expired - please log out and log back in")
            else:
                raise Exception(f"Database error: {str(db_error)}")
        
    except Exception as e:
        error_msg = f"Error saving analysis: {str(e)}"
        logger.error(f"=== SAVE ERROR: {error_msg} ===")
        raise Exception(error_msg)

def get_saved_analyses(user):
    """Get all saved analyses for a user."""
    try:
        # Get user ID with fallback
        user_id = user.get('localId')
        if not user_id:
            user_id = user.get('email', 'unknown_user')
            logger.warning(f"No localId found, using email as fallback: {user_id}")
        
        # Get token for authenticated request
        token = user.get('idToken')
        if not token:
            logger.warning("No authentication token found, returning empty list")
            return []
        
        analyses = db.child("analyses").child(user_id).get(token)
        
        if analyses.each():
            logger.info(f"Retrieved {len(analyses.each())} saved analyses for user {user_id}")
            return [item.val() for item in analyses.each()]
        else:
            logger.info("No saved analyses found")
            return []
            
    except Exception as e:
        logger.error(f"Error getting saved analyses: {str(e)}")
        return []
# praga/main.py

import streamlit as st
import os
from datetime import datetime
import time
import pytz

# Import utility functions and page modules
from utils import init_ai_service_client
import page_materials_upload
import page_materials_analysis
import page_chat
import page_explainer
import page_quiz
import page_web_analyzer

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Educational AI Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if 'ai_client' not in st.session_state:
    st.session_state.ai_client = init_ai_service_client()
# 'data_context_loaded' is now replaced by checking if 'processed_data' exists in the session
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

ai_client = st.session_state.ai_client

# --- Main Title and Information ---
st.title("🎓 Educational AI Platform")
st.caption("An interactive platform for didactic analysis, content generation, and AI-assisted learning.")

if ai_client is None:
    st.error("The AI service could not be initialized. Functionality is limited.")

# --- Navigation ---
st.sidebar.title("Navigation Menu")

context_is_loaded = st.session_state.processed_data is not None

menu_options = {
    "📚 Upload & Process Materials": "upload",
    "📊 Didactic Analysis vs. Competencies": "materials_analysis",
    "💬 AI Chat Based on Materials": "chat",
    "💡 Topic Explainer from Materials": "explainer",
    "❓ Quiz Generator": "quiz",
    "🌐 Web & Video Analyzer": "web_analyzer"
}

disabled_options = []
if not context_is_loaded:
    disabled_options = [
        "📊 Didactic Analysis vs. Competencies",
        "💬 AI Chat Based on Materials",
        "💡 Topic Explainer from Materials",
        "❓ Quiz Generator"
    ]

choice_label = st.sidebar.radio(
    "Choose a module:",
    options=menu_options.keys(),
    captions=["" if opt not in disabled_options else "Requires material processing" for opt in menu_options.keys()],
    key="main_nav_radio"
)

st.sidebar.markdown("---")

# --- Display Selected Page ---
current_page = menu_options[choice_label]

if choice_label in disabled_options:
    st.warning(f"Please upload and process a folder with materials in the 'Upload & Process Materials' module to access '{choice_label}'.")
    st.stop()

if current_page == "upload":
    page_materials_upload.render_page(ai_client)
elif current_page == "materials_analysis":
    page_materials_analysis.render_page(ai_client)
elif current_page == "chat":
    page_chat.render_page(ai_client)
elif current_page == "explainer":
    page_explainer.render_page(ai_client)
elif current_page == "quiz":
    page_quiz.render_page(ai_client)
elif current_page == "web_analyzer":
    page_web_analyzer.render_page(ai_client)

# --- Sidebar Information ---
st.sidebar.markdown("---")
st.sidebar.info("Educational AI Platform v2.1")
try:
    # This can be localized if needed
    london_tz = pytz.timezone('Europe/London')
    current_time_obj = datetime.now(london_tz)
    st.sidebar.markdown(f"Current Time (London):<br>**{current_time_obj.strftime('%d-%b-%Y %H:%M:%S')}**", unsafe_allow_html=True)
except Exception:
    st.sidebar.markdown(f"Server Time: {time.strftime('%d-%b-%Y %H:%M:%S')}")
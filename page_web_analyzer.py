# praga/page_web_analyzer.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import subprocess
import os
import uuid
from pydub import AudioSegment
import speech_recognition as sr

from utils import (
    process_direct_with_ai_service,
    get_curriculum_context,
    create_document_word
)

def download_audio_from_youtube(url, output_path):
    command = ["yt-dlp", "-x", "--audio-format", "wav", "-o", f"{output_path}.%(ext)s", url]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return f"{output_path}.wav"
    except subprocess.CalledProcessError as e:
        st.error(f"Error downloading audio: {e.stderr}")
        return None

def transcribe_audio_chunks(audio_path, language="en-US"):
    if not os.path.exists(audio_path): return "Error: Audio file not found."
    recognizer = sr.Recognizer()
    full_transcript = ""
    sound = AudioSegment.from_wav(audio_path)
    chunk_length_ms = 60 * 1000  # 60 seconds
    chunks = [sound[i:i + chunk_length_ms] for i in range(0, len(sound), chunk_length_ms)]
    progress_bar = st.progress(0, text="Transcribing audio segments...")
    for i, chunk in enumerate(chunks):
        chunk_filename = f"temp_chunk_{i}.wav"
        chunk.export(chunk_filename, format="wav")
        with sr.AudioFile(chunk_filename) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language=language)
                full_transcript += text + " "
            except sr.UnknownValueError:
                full_transcript += "[unintelligible portion] "
            except sr.RequestError:
                full_transcript += "[transcription service error] "
        os.remove(chunk_filename)
        progress_bar.progress((i + 1) / len(chunks), text=f"Transcribed segment {i+1}/{len(chunks)}...")
    progress_bar.empty()
    return full_transcript

def render_page(ai_client):
    st.header("🌐 External Resource Analyzer (Web & Video)")

    if 'extracted_content' not in st.session_state: st.session_state.extracted_content = None
    if 'content_source_url' not in st.session_state: st.session_state.content_source_url = ""

    tab_web, tab_video = st.tabs(["**Analyze Web Page**", "**Analyze YouTube Video**"])

    with tab_web:
        web_url = st.text_input("Enter the web page URL:", key="web_url")
        if st.button("🔗 Extract Text from Web", key="extract_web"):
            if web_url:
                with st.spinner("Extracting text..."):
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        response = requests.get(web_url, headers=headers, timeout=20)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')
                        for script in soup(["script", "style", "nav", "footer", "header"]): script.extract()
                        text = soup.get_text(separator='\n', strip=True)
                        st.session_state.extracted_content = text
                        st.session_state.content_source_url = web_url
                        st.success("Extraction complete!")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
            else:
                st.warning("Please enter a URL.")

    with tab_video:
        yt_url = st.text_input("Enter the YouTube video URL:", key="yt_url")
        if st.button("🎬 Extract Transcript from Video", key="extract_video"):
            if yt_url:
                with st.spinner("Preparing video processing..."):
                    audio_id = str(uuid.uuid4())[:8]
                    output_audio_path = f"temp_audio_{audio_id}"
                    st.info("Step 1/3: Downloading audio...")
                    downloaded_audio_file = download_audio_from_youtube(yt_url, output_audio_path)
                    if downloaded_audio_file:
                        st.info("Step 2/3: Transcribing...")
                        transcript = transcribe_audio_chunks(downloaded_audio_file)
                        os.remove(downloaded_audio_file)
                        st.info("Step 3/3: Transcription finished.")
                        st.session_state.extracted_content = transcript
                        st.session_state.content_source_url = yt_url
                        st.success("Transcript extraction complete!")
            else:
                st.warning("Please enter a YouTube URL.")

    if st.session_state.extracted_content:
        st.markdown("---")
        st.header(f"AI Analysis for Extracted Content")
        with st.expander("Show extracted text", expanded=False):
            st.text_area("Extracted Text", st.session_state.extracted_content, height=250)
            
        content_for_ai = st.session_state.extracted_content
        if len(content_for_ai) > 18000:
            content_for_ai = content_for_ai[:18000] + " [TRUNCATED CONTEXT]"

        with st.container(border=True):
            st.subheader("1. Generate Summary")
            summary_complexity = st.select_slider("Choose summary complexity:", ["Key points", "Short summary", "Detailed summary"])
            if st.button("📄 Generate Summary", key="generate_summary"):
                with st.spinner("The AI is generating the summary..."):
                    system_prompt = "You are an AI assistant expert in synthesizing information."
                    user_prompt = f"Generate a '{summary_complexity}' type summary for the following text:\n\n{content_for_ai}"
                    summary = process_direct_with_ai_service(user_prompt, system_prompt, ai_client)
                    st.session_state.generated_summary = summary
            if 'generated_summary' in st.session_state:
                st.markdown(st.session_state.generated_summary)
                summary_title = "External_Source_Summary"
                st.download_button("⬇️ Download (.docx)", create_document_word(st.session_state.generated_summary, title=summary_title), f"{summary_title}.docx")

        with st.container(border=True):
            st.subheader("2. Analysis Against Curriculum")
            curriculum_context, num_files = get_curriculum_context()
            if curriculum_context:
                st.info(f"The extracted content will be compared with the curriculum from the {num_files} files.")
                if st.button("🔬 Analyze vs. Curriculum", key="analyze_vs_curriculum", type="primary"):
                    with st.spinner("The AI is comparing the resource with the curriculum..."):
                        system_prompt = "You are an expert in curriculum design. Analyze an external resource (Context 2) in relation to a given curriculum (Context 1) and produce an analysis report."
                        user_prompt = (
                            "Analyze how 'Context 2' aligns with 'Context 1'. The report must contain:\n"
                            "1. **Covered Competencies:** Which curriculum competencies are covered by the resource?\n"
                            "2. **New Concepts Introduced:** What new topics does the resource bring?\n"
                            "3. **Integration Recommendations:** How can the resource be used in the classroom?\n\n"
                            f"--- CONTEXT 1: CURRICULUM ---\n{curriculum_context}\n\n"
                            f"--- CONTEXT 2: EXTERNAL RESOURCE ---\n{content_for_ai}"
                        )
                        analysis_report = process_direct_with_ai_service(user_prompt, system_prompt, ai_client, {"max_tokens": 4000})
                        st.session_state.curriculum_analysis_report = analysis_report
            else:
                st.warning("The curriculum is not loaded.")
            if 'curriculum_analysis_report' in st.session_state:
                st.markdown(st.session_state.curriculum_analysis_report)
                report_title = "Analysis_Resource_vs_Curriculum"
                st.download_button("⬇️ Download Analysis Report (.docx)", create_document_word(st.session_state.curriculum_analysis_report, title=report_title), f"{report_title}.docx")
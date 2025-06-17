# praga/page_materials_upload.py

import streamlit as st
import os
from utils import extract_text_from_file

def render_page(ai_client):
    st.header("📚 Upload & Process Didactic Materials")

    st.info(
        "**Step 1:** Upload your didactic materials (.pdf, .docx, .pptx, .txt) using the button below or by 'drag and drop'. You can select multiple files at once.\n\n"
        "**Step 2:** After the files appear in the list, press the 'Process Uploaded Materials' button. The application will extract the text and create a centralized knowledge base for your session."
    )

    uploaded_files = st.file_uploader(
        "Select files for analysis",
        type=['pdf', 'docx', 'pptx', 'txt', 'md'],
        accept_multiple_files=True,
        key="material_uploader"
    )

    if st.button("🚀 Process Uploaded Materials", type="primary"):
        if uploaded_files:
            extracted_data = {}
            progress_bar = st.progress(0, text="Extracting text from files...")

            for i, file in enumerate(uploaded_files):
                progress_bar.progress((i + 1) / len(uploaded_files), text=f"Processing: {file.name}")
                text = extract_text_from_file(file)
                if text:
                    extracted_data[file.name] = text

            if not extracted_data:
                st.error("Could not extract text from any of the provided files.")
                st.stop()
            
            # Store extracted data in the session state for multi-client support
            st.session_state.processed_data = extracted_data
            
            progress_bar.empty()
            st.success(f"Extracted content from {len(extracted_data)} files and saved the knowledge base for this session.")
            st.rerun()

        else:
            st.warning("Please upload at least one file before processing.")

    st.markdown("---")

    st.subheader("Knowledge Base Status")
    if 'processed_data' in st.session_state and st.session_state.processed_data:
        st.success(f"✅ Knowledge base for this session has been successfully loaded.")
        with st.expander("Show processed files"):
            data = st.session_state.processed_data
            st.write(f"**{len(data)}** files have been processed:")
            file_list_md = "\n".join([f"- `{file}`" for file in data.keys()])
            st.markdown(file_list_md)
    else:
        st.warning("❌ No knowledge base is loaded for this session. Please upload and process materials.")
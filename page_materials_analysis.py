# praga/page_materials_analysis.py

import streamlit as st
import pandas as pd
import json
from utils import (
    process_direct_with_ai_service,
    format_cell_for_custom_display,
    get_curriculum_context,
    DEFAULT_COMPETENCIES_SPECIFIC,
    MATERIAL_CATEGORIES,
    COVERAGE_LEGEND_EN_KEYS_FOR_AI,
    create_document_word
)

def generate_analysis_report(ai_client, analysis_df, competencies_dict):
    st.info("🤖 Generating pedagogical report...")
    analysis_summary = []
    for comp_id, row in analysis_df.iterrows():
        comp_desc = competencies_dict.get(comp_id, "N/A")
        analysis_summary.append(f"Competency {comp_id} ('{comp_desc}'):")
        for cat, value in row.items():
            if "Missing" not in value and "Lipsă" not in value:
                analysis_summary.append(f"- Category '{cat}': {value}")
    analysis_text_for_ai = "\n".join(analysis_summary)
    system_prompt = (
        "You are an expert in pedagogy. Analyze a competency coverage report and generate a detailed, structured, and professional narrative report."
    )
    user_prompt = (
        f"Based on the following analysis, generate a detailed pedagogical report. For each competency, include the sections: 'Coverage Summary', 'Qualitative Assessment' (High, Medium, Needs Supplementary Materials), and concrete 'Improvement Suggestions'. At the end, add 'General Conclusions and Recommendations'.\n\n"
        f"--- ANALYSIS DATA ---\n{analysis_text_for_ai}\n--- END DATA ---"
    )
    with st.spinner("The AI pedagogical expert is writing the report..."):
        report_content = process_direct_with_ai_service(
            user_prompt, system_prompt, ai_client, {"max_tokens": 4000, "temp": 0.6}
        )
    if "Error" in report_content:
        st.error(f"The AI encountered an error: {report_content}")
        return None
    st.success("The report was generated successfully!")
    return report_content

def render_page(ai_client):
    st.header("📊 Didactic Analysis vs. Competencies")

    # Initialize session state
    if 'competencies_dict' not in st.session_state:
        st.session_state.competencies_dict = DEFAULT_COMPETENCIES_SPECIFIC.copy()
    if 'analysis_df' not in st.session_state:
        st.session_state.analysis_df = None
    if 'competencies_text_for_manual_edit' not in st.session_state:
        st.session_state.competencies_text_for_manual_edit = "\n".join(
            [f"{cid}: {cdesc}" for cid, cdesc in st.session_state.competencies_dict.items()]
        )
    
    context, num_files = get_curriculum_context()
    if not context:
        st.error("The knowledge base is not loaded. Please process the materials in the upload module.")
        st.stop()

    st.subheader("Step 1: Define Specific Competencies")

    if st.button("🤖 Generate Competencies from Materials (AI)"):
        with st.spinner("The AI is analyzing the materials to suggest competencies..."):
            max_context = 20000
            truncated_context = context[:max_context] + "..." if len(context) > max_context else context
            
            system_prompt_comp = "You are an expert in pedagogy. Analyze the educational text and formulate a list of 8-10 key competencies. Respond ONLY with the list, each competency on a new line, in the format 'CX: Description'."
            user_prompt_comp = f"Based on the following text extracted from didactic materials, identify and list the main specific competencies:\n\n{truncated_context}"
            
            ai_competencies = process_direct_with_ai_service(user_prompt_comp, system_prompt_comp, ai_client, {"max_tokens": 1000})
            
            if ai_competencies and "Error" not in ai_competencies:
                st.session_state.competencies_text_for_manual_edit = ai_competencies
                st.success("AI-suggested competencies have been added to the box below. Review and save.")
                st.rerun()
            else:
                st.error("Automatic competency generation failed.")

    st.write("Edit the competencies (format: `C1: Description`) or generate them automatically using the button above.")
    edited_competencies_text = st.text_area(
        "Specific competencies (edit and save):",
        value=st.session_state.competencies_text_for_manual_edit,
        height=250,
        key="manual_comp_input_area"
    )
    if st.button("✔️ Save Competencies", key="save_manual_comp_button"):
        new_comp_dict = {}
        for line in edited_competencies_text.strip().split('\n'):
            if ':' in line:
                cid, cdesc = line.split(':', 1)
                new_comp_dict[cid.strip()] = cdesc.strip()
        st.session_state.competencies_dict = new_comp_dict
        st.session_state.analysis_df = None
        st.success(f"{len(new_comp_dict)} competencies saved.")
        st.rerun()

    if st.session_state.competencies_dict:
        st.markdown("---")
        with st.expander("Show/Hide Current Competencies", expanded=False):
            for cid, cdesc in st.session_state.competencies_dict.items():
                st.markdown(f"**{cid}**: {cdesc}")

    st.subheader("Step 2: Generate Analysis Table")
    
    files_data = st.session_state.get('processed_data', {})
    st.write(f"**{len(files_data)}** files from the knowledge base will be analyzed.")

    if st.button("🚀 Generate Analysis Table", key="analyze_materials_button", type="primary"):
        st.warning("This detailed analysis is more reliable but may take a long time. Please be patient.")
        
        analysis_df_in_progress = pd.DataFrame(
            index=list(st.session_state.competencies_dict.keys()),
            columns=MATERIAL_CATEGORIES
        ).fillna(f"Missing {COVERAGE_LEGEND_EN_KEYS_FOR_AI['Missing']}")

        total_cells = len(st.session_state.competencies_dict) * len(MATERIAL_CATEGORIES)
        progress_bar = st.progress(0, text=f"AI analysis in progress... 0/{total_cells} cells processed.")
        
        files_summary_prompt_part = "\n".join(
            [f"- File: '{name}', Content summary: {content[:200]}..." for name, content in files_data.items()]
        )
        
        cells_processed = 0
        for comp_id, comp_desc in st.session_state.competencies_dict.items():
            for category in MATERIAL_CATEGORIES:
                system_prompt_cell = "You are an AI assistant focused on a single task: analyze if the provided files match a specific competency AND a material category. Be optimistic."
                user_prompt_cell = (
                    f"Do any of the files below match the category **'{category}'** AND cover the competency **'{comp_id}: {comp_desc}'**?\n\n"
                    f"AVAILABLE FILES:\n{files_summary_prompt_part}\n\n"
                    f"Respond ONLY with the names of the relevant files, followed by (✅) for complete coverage or (🤔) for partial. Separate them by comma. If none match, respond ONLY with 'Missing'."
                )

                ai_response = process_direct_with_ai_service(
                    user_prompt_cell, system_prompt_cell, ai_client,
                    {"max_tokens": 500, "temp": 0.1}
                )

                if ai_response and "Error" not in ai_response and "Missing" not in ai_response:
                    analysis_df_in_progress.loc[comp_id, category] = ai_response
                
                cells_processed += 1
                progress_bar.progress(cells_processed / total_cells, text=f"AI analysis... {cells_processed}/{total_cells} cells. (Comp: {comp_id})")

        st.session_state.analysis_df = analysis_df_in_progress
        progress_bar.empty()
        st.success("AI analysis complete!")
        st.rerun()

    if st.session_state.analysis_df is not None:
        st.subheader("Step 3: Analysis Results")
        df_display = st.session_state.analysis_df.applymap(format_cell_for_custom_display)
        st.markdown(df_display.to_html(escape=False), unsafe_allow_html=True)
        st.markdown("---")
        
        st.subheader("Generate Detailed Pedagogical Report")
        if st.button("📝 Generate Report (.docx)", key="generate_report_button"):
            report_text = generate_analysis_report(ai_client, st.session_state.analysis_df, st.session_state.competencies_dict)
            if report_text:
                st.session_state.generated_report_text = report_text
        
        if 'generated_report_text' in st.session_state:
            with st.expander("Preview Generated Report", expanded=True):
                st.markdown(st.session_state.generated_report_text)
            
            report_title = "Pedagogical_Report_Material_Analysis"
            word_buffer = create_document_word(st.session_state.generated_report_text, title=report_title)
            st.download_button(
                label="⬇️ Download Report (.docx)",
                data=word_buffer,
                file_name=f"{report_title}.docx"
            )
# praga/page_quiz.py

import streamlit as st
import json
import re
from utils import (
    process_direct_with_ai_service,
    get_curriculum_context,
    create_document_word,
    extract_text_from_file,
)

def create_student_version_from_teacher_version(teacher_text):
    """
    Processes the teacher's version text and removes the scoring guide and answers
    to create the student's version.
    """
    lines = teacher_text.split('\n')
    student_lines = []
    in_scoring_guide = False
    in_answer = False

    for line in lines:
        # English keywords for parsing
        if line.strip().lower().startswith('# scoring guide') or line.strip().lower().startswith('## scoring guide'):
            in_scoring_guide = True
            continue
        if line.strip().startswith('## '): # A new section (e.g., Bloom category) ends the guide
            in_scoring_guide = False
        if line.strip().lower().startswith('#### correct answer') or line.strip().lower().startswith('**correct answer'):
            in_answer = True
            continue
        if line.strip().startswith('### '): # A new question ends the previous answer
            in_answer = False
        if not in_scoring_guide and not in_answer:
            student_lines.append(line)
            
    return "\n".join(student_lines)

def render_page(ai_client):
    st.header("❓ Quiz & Assessment")

    if not ai_client:
        st.error("AI service is not available.")
        st.stop()
    
    def clear_barem_state():
        keys_to_delete = ['generated_barem', 'source_test_filename']
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]

    tab1, tab2 = st.tabs(["**Quiz Generator**", "**Analyze & Score Existing Test**"])

    with tab1:
        st.subheader("Generate a New Quiz from Materials")
        context, num_files = get_curriculum_context()

        if not context:
            st.error("The knowledge base is not loaded.")
            st.stop()
        
        st.info(f"The quiz will be generated based on the content of the **{num_files}** processed files.")

        quiz_topic = st.text_input("Main topic of the quiz:", key="quiz_topic", placeholder="E.g.: 2D geometric transformations")
        
        quiz_difficulty = st.select_slider("General difficulty level:", options=["Easy", "Medium", "Difficult"], value="Medium")
        
        st.markdown("**Define the test structure according to Bloom's Taxonomy:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            num_knowledge = st.slider("No. of Knowledge/Comprehension items:", 0, 10, 3)
        with col2:
            num_application = st.slider("No. of Application/Analysis items:", 0, 10, 3)
        with col3:
            num_synthesis = st.slider("No. of Synthesis/Evaluation items:", 0, 10, 2)
        
        total_questions = num_knowledge + num_application + num_synthesis
        st.caption(f"Total number of questions: **{total_questions}**")

        if st.button("🎲 Generate Quiz", type="primary", key="generate_quiz_button"):
            if not quiz_topic or total_questions == 0:
                st.warning("Please enter the topic and select at least one question.")
            else:
                with st.spinner("Step 1/2: Identifying relevant materials..."):
                    all_files_data = st.session_state.get('processed_data', {})
                    
                    file_list_str = ", ".join(all_files_data.keys())
                    filter_prompt = f"From the list: {file_list_str}, which files are most relevant to the topic '{quiz_topic}'? Respond ONLY with a comma-separated list of filenames."
                    relevant_files_str = process_direct_with_ai_service(filter_prompt, "You are a library assistant.", ai_client, {"max_tokens": 500})
                    
                    focused_context = ""
                    if relevant_files_str and "Error" not in relevant_files_str:
                        relevant_files = [f.strip().strip("'\"") for f in relevant_files_str.split(',')]
                        for file_name in relevant_files:
                            if file_name in all_files_data:
                                focused_context += f"--- Content from '{file_name}' ---\n{all_files_data[file_name]}\n\n"
                    
                    if not focused_context:
                        st.warning("Filtering failed, using the full context.")
                        focused_context = context

                with st.spinner(f"Step 2/2: Generating the quiz from relevant materials..."):
                    system_prompt = (
                        "You are an expert in pedagogy. Your task is to create a complete quiz FOR THE TEACHER, based STRICTLY on the provided text. "
                        "Your response must be a single, well-structured Markdown document. FOLLOW THIS STRUCTURE:\n"
                        "1. Start with a level 1 heading for the Scoring Guide. E.g.: `# Scoring Guide and Rubric`.\n"
                        "2. Continue with the detailed text of the guide.\n"
                        "3. Use level 2 headings for the Bloom categories. E.g.: `## Knowledge/Comprehension`.\n"
                        "4. Use level 3 headings for each question. E.g.: `### Question 1`.\n"
                        "5. Immediately after each question, add the answer under a level 4 heading. E.g.: `#### Correct Answer:`."
                    )
                    user_prompt = (
                        f"Generate a quiz about '{quiz_topic}', with '{quiz_difficulty}' difficulty, based on the following text:\n\n{focused_context}\n\n"
                        f"Structure: {num_knowledge} Knowledge items, {num_application} Application/Analysis items, {num_synthesis} Synthesis/Evaluation items."
                    )
                    
                    teacher_version_raw = process_direct_with_ai_service(
                        user_prompt, system_prompt, ai_client, {"max_tokens": 4000, "temp": 0.7}
                    )

                if teacher_version_raw and "Error" not in teacher_version_raw and "Question" in teacher_version_raw:
                    st.session_state.teacher_version = teacher_version_raw
                    st.session_state.student_version = create_student_version_from_teacher_version(teacher_version_raw)
                    st.session_state.quiz_topic_generated = quiz_topic
                    st.success("The quiz has been generated successfully!")
                else:
                    st.error("Generation failed.")
                    with st.expander("Click here to see the raw response from the AI"):
                        st.text(teacher_version_raw or "The AI did not return any content.")

        if 'teacher_version' in st.session_state:
            st.markdown("---")
            col_t, col_s = st.columns(2)
            with col_t:
                with st.expander("Show Teacher Version"):
                    st.markdown(st.session_state.teacher_version)
            with col_s:
                with st.expander("Show Student Version (auto-generated)"):
                    st.markdown(st.session_state.student_version)
            
            dl_col1, dl_col2 = st.columns(2)
            quiz_title = f"Quiz_{st.session_state.quiz_topic_generated.replace(' ', '_')}"
            
            with dl_col1:
                st.markdown("#### Student Version")
                student_word = create_document_word(st.session_state.student_version, title=f"Student Quiz: {st.session_state.quiz_topic_generated}")
                st.download_button("⬇️ Download (.docx)", student_word, f"{quiz_title}_Student.docx")
            with dl_col2:
                st.markdown("#### Teacher Version")
                teacher_word = create_document_word(st.session_state.teacher_version, title=f"Teacher Quiz: {st.session_state.quiz_topic_generated}")
                st.download_button("⬇️ Download (.docx)", teacher_word, f"{quiz_title}_Teacher.docx")

    with tab2:
        st.subheader("Generate a Scoring Guide for an Uploaded Test")
        
        uploaded_test_file = st.file_uploader(
            "Upload the test file:", 
            type=['docx', 'pdf', 'txt'], 
            key="test_uploader",
            on_change=clear_barem_state
        )

        if st.button("🔬 Generate Scoring Guide", key="generate_barem_button"):
            if uploaded_test_file:
                test_text = extract_text_from_file(uploaded_test_file)
                if test_text:
                    system_prompt = "You are an expert in docimology. Analyze the text of a test and develop a detailed and fair scoring and grading guide."
                    user_prompt = (
                        "Analyze the following test text and create a professional 'Scoring and Grading Guide'. For each item:\n"
                        "1. Identify the targeted cognitive level (Bloom's Taxonomy).\n2. Propose a score.\n3. Clearly describe the scoring criteria.\n4. Provide a model of the correct answer.\n\n"
                        f"--- TEST TEXT ---\n{test_text}\n--- END TEXT ---"
                    )
                    with st.spinner("The assessment expert is building the guide..."):
                        barem_content = process_direct_with_ai_service(user_prompt, system_prompt, ai_client)
                    
                    st.session_state.generated_barem = barem_content
                    st.session_state.source_test_filename = uploaded_test_file.name
                    st.rerun()
            else:
                st.warning("Please upload a file.")
        
        if 'generated_barem' in st.session_state:
            st.markdown("---")
            st.subheader("Generated Scoring Guide")
            st.markdown(st.session_state.generated_barem)
            
            source_filename = st.session_state.get('source_test_filename', 'unknown_test.txt')
            barem_title = f"ScoringGuide_generated_for_{source_filename.split('.')[0]}"
            
            barem_word = create_document_word(
                st.session_state.generated_barem, 
                title=f"Scoring Guide for {source_filename}"
            )
            
            st.download_button(
                label="⬇️ Download Guide (.docx)",
                data=barem_word,
                file_name=f"{barem_title}.docx"
            )
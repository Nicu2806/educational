# praga/page_explainer.py

import streamlit as st
from utils import (
    process_direct_with_ai_service,
    get_curriculum_context,
    create_document_word,
    create_presentation_from_text
)

def render_page(ai_client):
    st.header("💡 Topic Explainer from Materials")

    if not ai_client:
        st.error("The AI service is not available for explanations.")
        st.stop()

    context, num_files = get_curriculum_context()

    if context:
        st.info(f"🤖 Explanations will be generated **exclusively** based on the content of the **{num_files}** processed files.")
    else:
        st.error("The knowledge base is not loaded.")
        st.stop()

    # Initialize session state variables
    if 'explanation_text' not in st.session_state:
        st.session_state.explanation_text = None
    if 'last_explained_topic' not in st.session_state:
        st.session_state.last_explained_topic = ""
    if 'presentation_text' not in st.session_state:
        st.session_state.presentation_text = None


    explainer_topic = st.text_input("What topic or concept would you like to have explained?", placeholder="E.g.: Parallel projections and perspectives")

    col1, col2, col3 = st.columns(3)
    with col1:
        explainer_audience = st.selectbox("Target audience level:", ["Middle School Student", "High School Student", "University Student", "Specialist (another perspective)"], index=1)
    with col2:
        explainer_length = st.select_slider("Desired length:", ["Short", "Medium", "Detailed"], value="Medium")
    with col3:
        explainer_style = st.selectbox("Teaching style:", ["Informative/Neutral", "Friendly/Conversational", "With many practical examples", "Using analogies and metaphors"])


    if st.button("🧠 Generate Explanation", type="primary"):
        if explainer_topic:
            # Reset states for a new explanation
            st.session_state.explanation_text = None
            st.session_state.presentation_text = None
            st.session_state.last_explained_topic = explainer_topic

            max_context_length = 25000
            if len(context) > max_context_length:
                context = context[:max_context_length] + "\n\n[CONTEXT TRUNCATED]"

            system_prompt = (
                "You are an expert pedagogue. Your task is to explain the given topic based STRICTLY on the provided text. Adapt the explanation for the specified audience, length, and style. Structure the response logically, using Markdown formatting."
            )
            user_prompt = (
                f"Please explain the topic: '{explainer_topic}'.\n"
                f"Adapt the explanation for a '{explainer_audience}', make it '{explainer_length}' in length, and use a '{explainer_style}' teaching style.\n\n"
                f"--- START PROVIDED MATERIALS ---\n{context}\n--- END PROVIDED MATERIALS ---"
            )

            with st.spinner(f"The AI is constructing an explanation for '{explainer_topic}'..."):
                explanation = process_direct_with_ai_service(
                    user_prompt, system_prompt, ai_client,
                    {"max_tokens": 2000, "temp": 0.7}
                )
                st.session_state.explanation_text = explanation
        else:
            st.warning("Please enter a topic to be explained.")

    if st.session_state.explanation_text:
        st.markdown("---")
        st.subheader(f"Explanation for: *{st.session_state.last_explained_topic}*")
        st.markdown(st.session_state.explanation_text, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("⬇️ Download Formats")
        
        # --- Word Document Download ---
        doc_title = f"Explanation_{st.session_state.last_explained_topic.replace(' ', '_')}"
        word_buffer = create_document_word(st.session_state.explanation_text, title=st.session_state.last_explained_topic)
        st.download_button(
            label="Download Explanation (.docx)",
            data=word_buffer,
            file_name=f"{doc_title}.docx"
        )
        
        st.markdown("---")
        
        # --- PowerPoint Presentation Generation and Download ---
        st.subheader("🖼️ Generate Presentation")
        if st.button("Generate Presentation from Explanation", key="generate_ppt"):
            with st.spinner("AI is structuring the content for a presentation..."):
                system_prompt_ppt = (
                    "You are an expert in creating educational presentations. Your task is to convert the given text into a clear PowerPoint presentation structure. Be concise and focus on the main ideas for each slide."
                )
                user_prompt_ppt = f"""
Based on the following text, create a clear educational presentation structure.
Each slide must contain:

- A clear title
- 2–3 short explanatory paragraphs (1-3 sentences each)
- If applicable, a list of 2–5 key points

Format:
## Slide 1
Slide Title
Explanatory paragraph 1.
Explanatory paragraph 2 (optional).
- Key point 1
- Key point 2

## Slide 2
...and so on.

Text to convert: '''{st.session_state.explanation_text}'''
                """
                presentation_text_response = process_direct_with_ai_service(user_prompt_ppt, system_prompt_ppt, ai_client, {"max_tokens": 3000})
                if presentation_text_response and "Error" not in presentation_text_response:
                    st.session_state.presentation_text = presentation_text_response
                    st.success("Presentation structure generated!")
                else:
                    st.error("Failed to generate presentation structure.")
        
        if st.session_state.get("presentation_text"):
            with st.expander("Preview Presentation Structure"):
                st.text(st.session_state.presentation_text)

            ppt_title = f"Presentation_{st.session_state.last_explained_topic.replace(' ', '_')}"
            ppt_buffer = create_presentation_from_text(st.session_state.presentation_text)
            st.download_button(
                label="Download Presentation (.pptx)",
                data=ppt_buffer,
                file_name=f"{ppt_title}.pptx"
            )
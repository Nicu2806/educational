# praga/page_chat.py

import streamlit as st
from utils import process_direct_with_ai_service, get_curriculum_context

def render_page(ai_client):
    st.header("💬 AI Chat Based on Materials")

    if not ai_client:
        st.error("AI service is not available for chat.")
        st.stop()

    context, num_files = get_curriculum_context()

    if context:
        st.info(f"🤖 The chat will respond **exclusively** based on the content of the **{num_files}** processed files.")
        system_prompt = (
            "You are an AI assistant specialized in answering questions based STRICTLY on the provided text. "
            "DO NOT use external knowledge. If the answer is not found in the text, state that clearly. "
            "Formulate the answers concisely and to the point, based on the following materials:\n\n"
            "--- START PROVIDED MATERIALS ---\n"
            f"{context}\n"
            "--- END PROVIDED MATERIALS ---"
        )
    else:
        # This check is now redundant due to the main.py guard, but good for safety.
        st.error("The knowledge base is not loaded. Please process a folder in the upload module.")
        st.stop()

    if 'chat_history' not in st.session_state or st.session_state.chat_history[0]['content'] != system_prompt:
        st.session_state.chat_history = [{"role": "system", "content": system_prompt}]

    chat_container = st.container(height=500, border=False)
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            elif msg["role"] == "assistant":
                st.chat_message("assistant").write(msg["content"])

    if user_input := st.chat_input("Ask a question about the uploaded materials..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.rerun()

    if st.session_state.chat_history[-1]["role"] == "user":
        with st.spinner("The AI is thinking..."):
            max_history_pairs = 5
            # Ensure the system prompt is always the first message
            messages_for_api = [st.session_state.chat_history[0]] + st.session_state.chat_history[-(2 * max_history_pairs):]
            
            ai_response = process_direct_with_ai_service(
                None, None, ai_client,
                {"messages_override": messages_for_api, "max_tokens": 1500, "temp": 0.7}
            )
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            st.rerun()
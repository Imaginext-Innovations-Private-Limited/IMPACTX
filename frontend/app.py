import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Socratic AI Tutor", page_icon="🎓", layout="wide")

# 1. Session State Initialization
if "guiding_messages" not in st.session_state:
    st.session_state.guiding_messages = []
if "ask_tutor_messages" not in st.session_state:
    st.session_state.ask_tutor_messages = []
if "mastery_score" not in st.session_state:
    st.session_state.mastery_score = 0
if "last_delta" not in st.session_state:
    st.session_state.last_delta = 0
if "current_question" not in st.session_state:
    st.session_state.current_question = 1
if "active_mode" not in st.session_state:
    st.session_state.active_mode = None

# 2. Sidebar Configuration
with st.sidebar:
    st.title("⚙️ Learner Setup")
    student_name = st.text_input("Student Name", value="Abu Zar Reehan")
    student_id = st.text_input("Student ID", value="SCA25MCA070")
    
    st.markdown("---")
    st.subheader("📄 Step 1: Upload Textbook (RAG)")
    uploaded_pdf = st.file_uploader("Upload PDF Reference", type=["pdf"])
    if uploaded_pdf and st.button("Index Textbook", use_container_width=True):
        with st.spinner("Indexing textbook chunks..."):
            try:
                files = {"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")}
                res = requests.post(f"{API_BASE}/documents/upload", files=files, timeout=60)
                if res.status_code == 200:
                    st.success(f"Indexed {uploaded_pdf.name} successfully!")
                else:
                    st.error(f"Upload failed: {res.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    st.markdown("---")
    st.subheader("📚 Step 2: Concept & Material")
    topic_mode = st.radio("Topic Selection", ["Type Custom Topic", "Pick From Presets"])
    if topic_mode == "Type Custom Topic":
        concept = st.text_input("Enter Topic/Concept from PDF", value="Cloud Computing (IaaS, PaaS, SaaS)").strip()
    else:
        concept = st.selectbox(
            "Select Preset Concept",
            ["Cloud Computing (IaaS, PaaS, SaaS)", "OSI Model Layers", "Supervised Learning", "Unsupervised Learning"]
        )
    
    difficulty_label = st.select_slider(
        "Difficulty Level",
        options=["Easy (1)", "Medium (2)", "Hard (3)"],
        value="Easy (1)"
    )
    difficulty_int = 1 if "Easy" in difficulty_label else (2 if "Medium" in difficulty_label else 3)
    
    st.markdown("---")
    if st.button("🗑️ Clear / Reset Session", use_container_width=True):
        st.session_state.guiding_messages = []
        st.session_state.ask_tutor_messages = []
        st.session_state.mastery_score = 0
        st.session_state.last_delta = 0
        st.session_state.current_question = 1
        st.session_state.active_mode = None
        st.rerun()

# 3. Main Interface Tabs
tab_chat, tab_teacher = st.tabs(["🎓 Socratic Learning Chat", "👩‍🏫 Teacher Dashboard"])

with tab_chat:
    st.header(f"📖 Concept: {concept}")
    
    # Progress Header
    col_q, col_score, col_bar = st.columns([1, 1, 2])
    with col_q:
        display_q = min(10, st.session_state.current_question)
        st.metric("Test Question", f"{display_q} of 10")
    with col_score:
        delta_str = f"+{st.session_state.last_delta}%" if st.session_state.last_delta > 0 else "0%"
        st.metric("Mastery Score", f"{st.session_state.mastery_score}%", delta=delta_str)
    with col_bar:
        st.write("Progress to 100% Mastery:")
        st.progress(min(1.0, max(0.0, st.session_state.mastery_score / 100.0)))
    
    st.markdown("---")

    # Mode Selector Buttons
    st.write("### Choose Your Learning Mode:")
    b1, b2 = st.columns(2)
    with b1:
        guiding_clicked = st.button(
            "🎯 Guiding Questions (10-Question Test, 10% each)", 
            use_container_width=True, 
            type="primary" if st.session_state.active_mode == "guiding" else "secondary"
        )
    with b2:
        ask_clicked = st.button(
            "💬 Ask the Tutor (Direct Q&A)", 
            use_container_width=True, 
            type="primary" if st.session_state.active_mode == "ask_tutor" else "secondary"
        )

    if guiding_clicked:
        st.session_state.active_mode = "guiding"
        if not st.session_state.guiding_messages:
            with st.spinner("Generating Question 1 of 10..."):
                try:
                    payload = {
                        "student_id": student_id,
                        "student_name": student_name,
                        "concept": concept,
                        "student_answer": "start",
                        "history": [],
                        "difficulty": difficulty_int,
                        "mode": "guiding",
                        "question_num": 1
                    }
                    res = requests.post(f"{API_BASE}/tutor/interact", json=payload, timeout=45).json()
                    st.session_state.guiding_messages.append({
                        "role": "assistant",
                        "feedback": res.get("feedback", f"Welcome, {student_name}! Let's start Question 1."),
                        "next_question": res.get("next_question", f"Question 1 of 10: In your words, what is the core purpose of {concept}?"),
                        "hint": res.get("hint", "Think of its everyday role and benefits."),
                    })
                    st.session_state.current_question = 1
                except Exception as e:
                    st.error(f"Error starting test: {e}")
        st.rerun()

    if ask_clicked:
        st.session_state.active_mode = "ask_tutor"
        if not st.session_state.ask_tutor_messages:
            st.session_state.ask_tutor_messages.append({
                "role": "assistant",
                "content": f"Hello {student_name}! What questions do you have about {concept}? Ask anything, and I will explain clearly."
            })
        st.rerun()

    if st.session_state.active_mode is None:
        st.info("👆 Please select one of the two buttons above to begin learning!")

    # MODE 1: Guiding Questions Mode
    elif st.session_state.active_mode == "guiding":
        st.info(f"🎯 **Active Mode: Guiding Questions.** Each correct answer awards +10%. You are on Question {min(10, st.session_state.current_question)} of 10.")
        
        for msg in st.session_state.guiding_messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["feedback"])
                    if msg.get("next_question"):
                        st.markdown(f"**{msg['next_question']}**")
                    # Guaranteed hint display
                    hint_text = msg.get("hint") or "Think about the primary definition and practical use cases."
                    if hint_text.strip():
                        with st.expander("💡 Need a Hint?"):
                            st.write(hint_text)

        if st.session_state.current_question > 10:
            st.success(f"🏆 **Test Finished! Your Final Mastery Score is {st.session_state.mastery_score}% out of 100%.**")
            st.balloons()
        else:
            user_input = st.chat_input(f"Type your answer for Question {st.session_state.current_question} of 10...")
            if user_input:
                st.session_state.guiding_messages.append({"role": "user", "content": user_input})
                
                hist = []
                for m in st.session_state.guiding_messages:
                    if m["role"] == "user":
                        hist.append({"role": "user", "content": m["content"]})
                    else:
                        hist.append({"role": "assistant", "content": f"{m.get('feedback', '')} {m.get('next_question', '')}"})

                with st.spinner("Evaluating your response..."):
                    try:
                        payload = {
                            "student_id": student_id,
                            "student_name": student_name,
                            "concept": concept,
                            "student_answer": user_input,
                            "history": hist,
                            "difficulty": difficulty_int,
                            "mode": "guiding",
                            "question_num": st.session_state.current_question
                        }
                        res = requests.post(f"{API_BASE}/tutor/interact", json=payload, timeout=45).json()
                        
                        st.session_state.guiding_messages.append({
                            "role": "assistant",
                            "feedback": res.get("feedback", "Good effort."),
                            "next_question": res.get("next_question", ""),
                            "hint": res.get("hint", "Consider the underlying architecture."),
                        })
                        
                        st.session_state.mastery_score = res.get("mastery_score", st.session_state.mastery_score)
                        st.session_state.last_delta = res.get("score_delta", 0)
                        st.session_state.current_question += 1
                    except Exception as e:
                        st.error(f"Error: {e}")
                st.rerun()

    # MODE 2: Ask the Tutor Mode
    elif st.session_state.active_mode == "ask_tutor":
        st.warning("💬 **Active Mode: Ask the Tutor.** Ask any question or request examples; full explanations are provided without tests or score changes.")
        
        for msg in st.session_state.ask_tutor_messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

        user_input = st.chat_input("Ask any question or request examples...")
        if user_input:
            st.session_state.ask_tutor_messages.append({"role": "user", "content": user_input})
            
            with st.spinner("Tutor is answering..."):
                try:
                    payload = {
                        "student_id": student_id,
                        "student_name": student_name,
                        "concept": concept,
                        "student_answer": user_input,
                        "history": [],
                        "difficulty": difficulty_int,
                        "mode": "ask_tutor",
                        "question_num": 1
                    }
                    res = requests.post(f"{API_BASE}/tutor/interact", json=payload, timeout=45).json()
                    st.session_state.ask_tutor_messages.append({
                        "role": "assistant",
                        "content": res.get("feedback", "Here is the explanation.")
                    })
                    st.session_state.last_delta = 0
                except Exception as e:
                    st.error(f"Error: {e}")
            st.rerun()

# 4. Teacher Dashboard Tab
with tab_teacher:
    st.header("👩‍🏫 Class Performance & Analytics")
    try:
        res = requests.get(f"{API_BASE}/teacher/analytics", timeout=10).json()
        records = res.get("records", [])
        concept_summary = res.get("concept_summary", [])
        student_summary = res.get("student_summary", [])
        
        if records:
            df = pd.DataFrame(records)
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Total Students", len(set(df["student_name"])))
            with k2:
                st.metric("Total Concepts Taught", len(set(df["concept"])))
            with k3:
                st.metric("Class Average Mastery", f"{round(df['mastery_score'].mean(), 1)}%")
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📊 Average Mastery by Concept")
                if concept_summary:
                    c_df = pd.DataFrame(concept_summary).set_index("concept")
                    st.bar_chart(c_df["avg_mastery"])
                else:
                    st.bar_chart(df.groupby("concept")["mastery_score"].mean())
            with c2:
                st.subheader("📈 Total Learning Attempts by Student")
                if student_summary:
                    s_df = pd.DataFrame(student_summary).set_index("student_name")
                    st.bar_chart(s_df["total_attempts"])
                else:
                    st.bar_chart(df.groupby("student_name")["attempts"].sum())

            st.markdown("---")
            st.subheader("📋 Student Progress Roster")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No learner records recorded yet. Complete questions in the Chat tab to view real-time charts!")
    except Exception as e:
        st.error(f"Error loading analytics: {e}")

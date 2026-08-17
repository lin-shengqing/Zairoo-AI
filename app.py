import streamlit as st
import ai_core

st.set_page_config(page_title="Zairoo AI - Math Engine", layout="wide")

st.title("Zairoo AI: P5 Math Engine")
st.markdown("Dynamic Question Generation and Semantic Auto-Marking")

# Initialize Session State
if "generated_problems" not in st.session_state:
    st.session_state.generated_problems = []

# ==========================================
# PART A: QUESTION GENERATOR UI
# ==========================================
st.header("Part A: Generate Verified Math Questions")

col1, col2 = st.columns(2)
with col1:
    topic = st.selectbox("Select Topic (Primary 5)", ["Fractions", "Ratio", "Percentage"])
with col2:
    count = st.number_input("Number of Questions (N)", min_value=1, max_value=5, value=1)

if st.button("Generate Questions"):
    with st.spinner("Generating and verifying math problems..."):
        try:
            problems = ai_core.generate_problem_set(topic, count)
            st.session_state.generated_problems = problems
            st.success("Questions generated and independently verified!")
        except Exception as e:
            st.error(f"Error generating questions: {str(e)}")

# Display Generated Problems
for i, prob in enumerate(st.session_state.generated_problems):
    with st.expander(f"Question {i+1}: {prob.question[:50]}...", expanded=True):
        st.markdown(f"**Question:** {prob.question}")
        st.markdown(f"**Correct Final Answer:** {prob.final_answer}")
        
        st.markdown("**Step-by-Step Solution:**")
        for step in prob.step_by_step_solution:
            st.markdown(f"- {step}")

st.divider()

# ==========================================
# PART B: AUTO-MARKER UI
# ==========================================
st.header("Part B: Auto-Marker")
st.markdown("Test the grading engine using one of the generated questions above, or enter custom data.")

if st.session_state.generated_problems:
    # Auto-fill dropdown from generated questions
    q_options = {p.question: p for p in st.session_state.generated_problems}
    selected_q = st.selectbox("Select a question to grade against:", list(q_options.keys()))
    active_problem = q_options[selected_q]
else:
    st.info("Generate some questions first to use the Auto-Marker, or it will run in standalone mode.")
    active_problem = None

st.subheader("Student Submission")
student_working = st.text_area("Student's Step-by-Step Working", placeholder="e.g., I multiplied 50 by 2, then divided by 10...")
student_answer = st.text_input("Student's Final Answer", placeholder="e.g., 3/5, 0.6, 60%")

if st.button("Grade Submission"):
    if not student_answer:
        st.warning("Please provide a student answer.")
    elif not active_problem:
        st.error("Please generate a question first.")
    else:
        with st.spinner("Grading submission..."):
            result = ai_core.grade_student_submission(
                question=active_problem.question,
                true_solution=active_problem.step_by_step_solution,
                true_answer=active_problem.final_answer,
                student_answer=student_answer,
                student_working=student_working
            )
            
            # Display Grading Results
            st.subheader("Grading Report")
            
            if result.is_final_answer_correct:
                st.success(f"Final Answer: Correct! (Score: {result.marks_awarded}/{result.max_marks})")
            else:
                st.error(f"Final Answer: Incorrect (Score: {result.marks_awarded}/{result.max_marks})")
                
            st.markdown("**Step-by-Step Analysis:**")
            for step in result.step_by_step_analysis:
                st.markdown(f"- {step}")
                
            st.info(f"**Teacher Feedback:** {result.constructive_feedback}")
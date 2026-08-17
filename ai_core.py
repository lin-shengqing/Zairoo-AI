import os
import json
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize standard OpenAI client but point it to the Vercel AI Gateway
client = OpenAI(
    base_url=os.environ.get("VERCEL_GATEWAY_URL"),
    api_key=os.environ.get("VERCEL_API_KEY")
)

# Use a strong model for math and reasoning
MODEL_NAME = "gpt-4o" 

# ==========================================
# PYDANTIC SCHEMAS (STRUCTURED OUTPUTS)
# ==========================================

class MathProblem(BaseModel):
    question: str = Field(description="The word problem text.")
    step_by_step_solution: list[str] = Field(description="Step-by-step breakdown of the math.")
    final_answer: str = Field(description="The exact final numerical answer with units if applicable.")

class VerificationResult(BaseModel):
    is_mathematically_sound: bool = Field(description="True if the math is flawless, False if there are errors.")
    error_details: str = Field(description="If false, explain the calculation error.")

class GradingResult(BaseModel):
    is_final_answer_correct: bool = Field(description="True if student's final answer matches the true value, regardless of format (e.g. 3/5 == 0.6).")
    step_by_step_analysis: list[str] = Field(description="Feedback on each step of the student's working.")
    marks_awarded: int = Field(description="Total marks awarded based on working and final answer.")
    max_marks: int = Field(description="Maximum possible marks for this question (default to 3).")
    constructive_feedback: str = Field(description="Overall encouraging feedback for the P5 student.")

# ==========================================
# PART A: GENERATOR & VALIDATOR LOOP
# ==========================================

def generate_single_problem(level: str, topic: str) -> MathProblem:
    """
    Generates a single math problem based on level and topic. 
    Uses an Agentic Loop (Generate -> Verify) to guarantee correctness.
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        # Step 1: Generation Agent
        completion = client.beta.chat.completions.parse(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": f"You are a Singapore MOE {level} Math curriculum expert. Create challenging but solvable word problems."},
                {"role": "user", "content": f"Generate a {level} math word problem about {topic}. Ensure calculations result in clean numbers."}
            ],
            response_format=MathProblem,
            temperature=0.7
        )
        
        draft_problem = completion.choices[0].message.parsed
        
        # Step 2: Verification Agent (Independent Critique)
        is_valid = verify_math_problem(draft_problem)
        
        if is_valid:
            return draft_problem
            
    # If it fails 3 times, raise an error to prevent hallucinated math from showing
    raise ValueError("Failed to generate a mathematically sound problem after maximum retries.")

def verify_math_problem(problem: MathProblem) -> bool:
    """
    Acts as an independent evaluator to recalculate the generated problem.
    This solves the LLM arithmetic hallucination issue.
    """
    verification = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a strict math auditor. Do not trust the provided solution. Calculate the answer yourself based ONLY on the question text."},
            {"role": "user", "content": f"Question: {problem.question}\nProvided Answer: {problem.final_answer}\nProvided Steps: {problem.step_by_step_solution}\n\nRe-calculate step-by-step. Does the arithmetic hold up perfectly?"}
        ],
        response_format=VerificationResult,
        temperature=0.0 # Zero temperature for deterministic auditing
    )
    
    return verification.choices[0].message.parsed.is_mathematically_sound

def generate_problem_set(level: str, topic: str, count: int) -> list[MathProblem]:
    """Generates N verified problems."""
    return [generate_single_problem(level, topic) for _ in range(count)]

# ==========================================
# PART B: AUTO-MARKER
# ==========================================

def grade_student_submission(question: str, true_solution: list[str], true_answer: str, student_answer: str, student_working: str) -> GradingResult:
    """
    Grades the student's submission semantically, handling format variations (0.6 vs 3/5).
    Evaluates both intermediate steps and final answers.
    """
    prompt = f"""
    You are an empathetic but accurate P5 Math Teacher. 
    
    Original Question: {question}
    Teacher's Correct Solution: {true_solution}
    Teacher's Final Answer: {true_answer}
    
    Student's Working: {student_working}
    Student's Final Answer: {student_answer}
    
    Instructions:
    1. Check if the student's final answer is mathematically equivalent to the teacher's (e.g., 60% == 0.6 == 3/5).
    2. Read their working. Award partial marks (out of 3 total) if they got intermediate steps correct but messed up the final calculation.
    3. Provide constructive feedback.
    """
    
    completion = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are an automated grading system for Singapore primary school math."},
            {"role": "user", "content": prompt}
        ],
        response_format=GradingResult,
        temperature=0.1
    )
    
    return completion.choices[0].message.parsed
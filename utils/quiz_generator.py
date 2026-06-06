from groq import Groq
import os

# GROQ CLIENT
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def generate_quiz(text, difficulty):

    prompt = f"""

You are Brain Byte AI.

Generate 5 {difficulty} multiple choice quiz questions
from the given content.

RULES:
- Create important conceptual MCQs
- Each question must have 4 options
- Mention correct answer clearly
- Keep questions educational
- Avoid repeated questions
- Keep options realistic
- Use only provided content
- Do not hallucinate

FORMAT:

Q: Question here

A. Option
B. Option
C. Option
D. Option

ANSWER: Correct Option

CONTENT:
{text[:4000]}

"""

    response = client.chat.completions.create(

        model="llama3-70b-8192",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.7
    )

    return response.choices[0].message.content
# FLASHCARD GENERATOR UTILS


# FOR PDF-BASED FLASHCARDS (existing)
def build_flashcard_prompt(text):

    prompt = f"""

You are Brain Byte AI.

Generate educational flashcards from the given summary.

RULES:
- Create important question-answer flashcards
- Keep answers concise
- Keep questions clear
- Avoid very long answers
- Focus on revision-friendly learning
- Use only the provided content
- Do not hallucinate

FORMAT:

Q: Question here
A: Answer here

Q: Another question
A: Another answer

CONTENT:
{text}

"""

    return prompt


# FOR LIVE CHAT FLASHCARDS (new)
def build_live_flashcard_prompt(topic):

    prompt = f"""

You are Brain Byte AI, a smart flashcard generator.

The user wants to study: {topic}

Generate 6 to 8 high quality flashcards on this topic.

RULES:
- Create clear, exam-focused questions
- Keep answers concise (1-3 sentences max)
- Cover different aspects of the topic
- Do not add any extra text, headings, or numbering
- Only output Q: and A: lines
- Do not hallucinate

STRICT FORMAT (follow exactly):

Q: Question here
A: Answer here

Q: Another question
A: Another answer

"""

    return prompt
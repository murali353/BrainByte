from flask import Flask, render_template, request, send_from_directory, jsonify
import os
import uuid
import traceback

# MARKDOWN
import markdown

# PDF READER
from PyPDF2 import PdfReader

# GROQ
from groq import Groq

# ENV
from dotenv import load_dotenv

# UTILS
from utils.text_cleaner import clean_pdf_text
from utils.summarizer import build_summary_prompt
from utils.chunker import chunk_text
from utils.flashcard_generator import build_flashcard_prompt, build_live_flashcard_prompt

# LOAD ENV
load_dotenv()

# API KEY
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("WARNING: GROQ_API_KEY is not set. AI features will not work.")

# GROQ CLIENT
client = Groq(api_key=api_key) if api_key else None

# FLASK APP
app = Flask(__name__)

# UPLOAD FOLDER
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# MAX FILE SIZE: 50MB
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# HOME PAGE
@app.route("/")
def home():

    return render_template(
        "login.html"
    )

# LOGIN PAGE
@app.route("/login")
def login():

    return render_template(
        "login.html"
    )

# SIGNUP PAGE
@app.route("/signup")
def signup():

    return render_template(
        "signup.html"
    )

# DASHBOARD PAGE
@app.route("/dashboard")
def dashboard():

    return render_template(
        "dashboard.html"
    )

# UPLOAD PAGE
@app.route(
    "/upload_notes",
    methods=["GET", "POST"]
)
def upload_notes():

    if request.method == "POST":

        file = request.files["file"]

        if file.filename != "":

            filepath = os.path.join(

                app.config["UPLOAD_FOLDER"],

                file.filename
            )

            file.save(filepath)

            return render_template(

                "upload.html",

                message="File Uploaded Successfully ✅",

                filename=file.filename
            )

    return render_template(
        "upload.html"
    )

# MY NOTES PAGE
@app.route("/my_notes")
def my_notes():

    files = os.listdir("uploads")

    return render_template(

        "my_notes.html",

        files=files
    )

# NOTE DETAIL PAGE
@app.route("/note_detail/<filename>")
def note_detail(filename):

    return render_template(

        "note_detail.html",

        filename=filename
    )

# OPEN FILE
@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(

        app.config["UPLOAD_FOLDER"],

        filename
    )

# ===== LECTURE AUDIO ROUTES =====

# LECTURE AUDIO PAGE
@app.route("/lecture_audio")
def lecture_audio():

    return render_template(
        "lecture_audio.html"
    )

# UPLOAD & TRANSCRIBE AUDIO — Uses Groq Whisper Cloud API (no local model needed)
@app.route("/upload_lecture", methods=["POST"])
def upload_lecture():

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]

    if audio_file.filename == "":
        return jsonify({"error": "No audio file selected"}), 400

    if not client:
        return jsonify({"error": "AI service is not configured. Please set GROQ_API_KEY."}), 500

    temp_path = None

    try:
        # Create uploads folder if it doesn't exist
        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])

        # Save file temporarily
        original_ext = os.path.splitext(audio_file.filename)[1] or ".mp3"
        temp_filename = f"temp_audio_{uuid.uuid4().hex}{original_ext}"
        temp_path = os.path.join(app.config["UPLOAD_FOLDER"], temp_filename)

        print(f"Saving audio to: {temp_path}")
        audio_file.save(temp_path)

        file_size = os.path.getsize(temp_path)
        print(f"File saved — size: {file_size} bytes")

        # Groq enforces 25MB for audio transcription
        if file_size > 25 * 1024 * 1024:
            os.remove(temp_path)
            return jsonify({"error": "File too large. Groq Whisper supports up to 25MB."}), 400

        # Transcribe using Groq Whisper cloud API (no local model needed)
        print("Transcribing via Groq Whisper API...")
        with open(temp_path, "rb") as f:
            transcription_response = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f,
                response_format="verbose_json"
            )

        transcribed_text = transcription_response.text
        detected_language = getattr(transcription_response, "language", "en") or "en"
        print("Transcription successful!")

        # Clean temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({
            "transcription": transcribed_text,
            "language": detected_language,
            "status": "success"
        })

    except Exception as e:
        print(f"ERROR in /upload_lecture: {str(e)}")
        traceback.print_exc()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({"error": str(e)}), 500

# GENERATE SUMMARY FROM TRANSCRIPTION
@app.route("/generate_lecture_summary", methods=["POST"])
def generate_lecture_summary():

    data = request.json
    transcription = data.get("transcription", "").strip()
    
    if not transcription:
        return jsonify({"error": "No transcription provided"}), 400
    
    prompt = f"""
You are Brain Byte AI, a smart study assistant.

Generate a detailed structured summary from this lecture transcription.

RULES:
- Use clear headings with ##
- Use bullet points under each heading
- Keep explanations concise
- Cover all important aspects
- Do not hallucinate

TRANSCRIPTION:
{transcription[:4000]}

FORMAT:
## Topic Name
- Key point 1
- Key point 2

## Next Topic
- Point 1
- Point 2
"""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        raw = chat_completion.choices[0].message.content
        
        return jsonify({
            "summary": raw,
            "raw_content": raw
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GENERATE FLASHCARDS FROM TRANSCRIPTION
@app.route("/generate_lecture_flashcards", methods=["POST"])
def generate_lecture_flashcards():

    data = request.json
    transcription = data.get("transcription", "").strip()
    
    if not transcription:
        return jsonify({"error": "No transcription provided"}), 400
    
    prompt = f"""
You are Brain Byte AI, a smart flashcard generator.

Generate as many flashcards as possible from this lecture transcription.

FORMAT:
Q: Question about the topic?
A: Answer to the question

RULES:
- Generate as many as possible
- Cover all key topics from lecture
- Each Q&A should be clear and concise
- No extra text or explanations
- One Q&A pair per line

TRANSCRIPTION:
{transcription[:4000]}
"""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        raw = chat_completion.choices[0].message.content
        flashcards = []
        
        lines = raw.split("\n")
        question = ""
        answer = ""
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("Q:"):
                question = line.replace("Q:", "").strip()
            elif line.startswith("A:"):
                answer = line.replace("A:", "").strip()
                
                if question and answer:
                    flashcards.append({
                        "question": question,
                        "answer": answer
                    })
                    question = ""
                    answer = ""
        
        return jsonify({
            "flashcards": flashcards,
            "raw_content": raw
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== LECTURE QUIZ ROUTE =====

# LECTURE QUIZ PAGE
@app.route("/lecture_quiz")
def lecture_quiz():
    return render_template(
        "lecture_quiz.html"
    )

# SAVE QUIZ RESULT TO FIRESTORE
@app.route("/save_quiz_result", methods=["POST"])
def save_quiz_result():
    try:
        data = request.json
        user_id = data.get("userId")
        topic = data.get("topic", "Lecture Audio")
        correct = data.get("correct", 0)
        total = data.get("total", 0)
        accuracy = int((correct / total * 100)) if total > 0 else 0
        
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 400
        
        # Save to Firestore (handled in lecture_quiz.html)
        return jsonify({
            "status": "success",
            "accuracy": accuracy
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GENERATE QUIZ FROM TRANSCRIPTION
@app.route("/generate_lecture_quiz", methods=["POST"])
def generate_lecture_quiz():

    data = request.json
    transcription = data.get("transcription", "").strip()
    
    if not transcription:
        return jsonify({"error": "No transcription provided"}), 400
    
    prompt = f"""
You are Brain Byte AI, a smart quiz generator.

Generate as many quiz questions as possible from this lecture transcription.

Mix these types (use each at least once):
- MCQ (multiple choice, 4 options)
- True/False
- Fill in the blank (use ___ for blank)

STRICT FORMAT:

TYPE: MCQ
Q: Question here?
A. Option 1
B. Option 2
C. Option 3
D. Option 4
ANSWER: A

TYPE: TF
Q: Statement here.
ANSWER: True

TYPE: FIB
Q: The ___ is the powerhouse of the cell.
ANSWER: mitochondria

RULES:
- Generate as many questions as possible
- Mix all 3 types, use each at least once
- Base questions ONLY on provided transcription
- No explanations
- No extra text

TRANSCRIPTION:
{transcription[:4000]}
"""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        raw = chat_completion.choices[0].message.content
        questions = []
        
        blocks = raw.strip().split("TYPE:")
        
        for block in blocks:
            block = block.strip()
            
            if not block:
                continue
            
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            
            if not lines:
                continue
            
            qtype = lines[0].strip()
            question = ""
            options = []
            answer = ""
            
            for line in lines[1:]:
                if line.startswith("Q:"):
                    question = line.replace("Q:", "").strip()
                elif (
                    line.startswith("A.")
                    or line.startswith("B.")
                    or line.startswith("C.")
                    or line.startswith("D.")
                ):
                    options.append(line)
                elif line.startswith("ANSWER:"):
                    answer = line.replace("ANSWER:", "").strip()
            
            if question and answer:
                questions.append({
                    "type": qtype,
                    "question": question,
                    "options": options,
                    "answer": answer
                })
        
        return jsonify({"questions": questions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== PDF ROUTES (EXISTING) =====

# AI SUMMARY PAGE
@app.route("/summary/<filename>")
def summary(filename):

    filepath = os.path.join(

        app.config["UPLOAD_FOLDER"],

        filename
    )

    text = ""

    reader = PdfReader(filepath)

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            text += page_text + " "

    cleaned_text = clean_pdf_text(text)

    chunks = chunk_text(

        cleaned_text,

        max_words=500
    )

    chunk_summaries = []

    try:

        for chunk in chunks:

            prompt = build_summary_prompt(
                chunk
            )

            chat_completion = client.chat.completions.create(

                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],

                model="llama-3.1-8b-instant",
            )

            chunk_summary = (

                chat_completion
                .choices[0]
                .message
                .content
            )

            chunk_summaries.append(
                chunk_summary
            )

        combined_summary = "\n\n".join(
            chunk_summaries
        )

        final_prompt = f"""

Create a clean structured summary from the given content.

RULES:
- Use headings
- Use bullet points
- Avoid repetition
- Keep concise explanations
- Use only provided content

CONTENT:
{combined_summary}

"""

        final_chat = client.chat.completions.create(

            messages=[
                {
                    "role": "user",
                    "content": final_prompt,
                }
            ],

            model="llama-3.1-8b-instant",
        )

        raw_summary = (

            final_chat
            .choices[0]
            .message
            .content
        )

        final_summary = markdown.markdown(
            raw_summary
        )

    except Exception as e:

        final_summary = f"""

<h2>Error while generating summary</h2>

<p>{str(e)}</p>

"""

    return render_template(

        "summary.html",

        summary=final_summary,

        filename=filename
    )

# FLASHCARDS PAGE (PDF based)
@app.route("/flashcards/<filename>")
def flashcards(filename):

    filepath = os.path.join(

        app.config["UPLOAD_FOLDER"],

        filename
    )

    pages_data = []

    reader = PdfReader(filepath)

    for i, page in enumerate(reader.pages):

        page_text = page.extract_text()

        if page_text:

            pages_data.append({

                "page": i + 1,

                "text": page_text
            })

    chunks = []

    for item in pages_data:

        cleaned_text = clean_pdf_text(
            item["text"]
        )

        page_chunks = chunk_text(

            cleaned_text,

            max_words=500
        )

        for chunk in page_chunks:

            chunks.append({

                "page": item["page"],

                "text": chunk
            })

    flashcards = []

    try:

        for chunk_data in chunks:

            prompt = build_flashcard_prompt(

                chunk_data["text"]
            )

            chat_completion = client.chat.completions.create(

                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],

                model="llama-3.1-8b-instant",
            )

            result = (

                chat_completion
                .choices[0]
                .message
                .content
            )

            flashcards.append({

                "content": result,

                "page": chunk_data["page"]
            })

        all_flashcards = []

        for item in flashcards:

            lines = item["content"].split("\n")

            question = ""

            answer = ""

            for line in lines:

                line = line.strip()

                if line.startswith("Q:"):

                    question = (

                        line.replace(
                            "Q:",
                            ""
                        )
                        .strip()
                    )

                elif line.startswith("A:"):

                    answer = (

                        line.replace(
                            "A:",
                            ""
                        )
                        .strip()
                    )

                    if question and answer:

                        all_flashcards.append({

                            "question": question,

                            "answer": answer,

                            "page": item["page"]
                        })

                        question = ""
                        answer = ""

        final_flashcards = all_flashcards

    except Exception as e:

        final_flashcards = [

            {
                "question": "Error",

                "answer": str(e),

                "page": "-"
            }
        ]

    return render_template(

        "flashcards.html",

        flashcards=final_flashcards,

        filename=filename
    )

# LIVE FLASHCARD CHAT PAGE
@app.route("/live_flashcards")
def live_flashcards():

    return render_template(
        "live_flashcards.html"
    )

# LIVE FLASHCARD API
@app.route("/generate_flashcards", methods=["POST"])
def generate_flashcards():

    data = request.json

    topic = data.get("topic", "").strip()

    if not topic:

        return jsonify({"error": "No topic provided"}), 400

    prompt = build_live_flashcard_prompt(topic)

    try:

        chat_completion = client.chat.completions.create(

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            model="llama-3.1-8b-instant",
        )

        raw = (

            chat_completion
            .choices[0]
            .message
            .content
        )

        flashcards = []

        lines = raw.split("\n")

        question = ""
        answer = ""

        for line in lines:

            line = line.strip()

            if line.startswith("Q:"):

                question = line.replace("Q:", "").strip()

            elif line.startswith("A:"):

                answer = line.replace("A:", "").strip()

                if question and answer:

                    flashcards.append({
                        "question": question,
                        "answer": answer
                    })

                    question = ""
                    answer = ""

        return jsonify({
            "flashcards": flashcards,
            "raw_content": raw
        })

    except Exception as e:

        return jsonify({"error": str(e)}), 500

# LIVE SUMMARY API
@app.route("/generate_summary", methods=["POST"])
def generate_summary():

    data = request.json

    topic = data.get("topic", "").strip()

    if not topic:

        return jsonify({"error": "No topic provided"}), 400

    prompt = f"""

You are Brain Byte AI, a smart study assistant.

Generate a detailed structured summary on: {topic}

RULES:
- Use clear headings with ##
- Use bullet points under each heading
- Keep explanations concise
- Cover all important aspects
- Do not hallucinate

FORMAT EXAMPLE:
## Introduction
- Point 1
- Point 2

## Key Concepts
- Point 1
- Point 2

"""

    try:

        chat_completion = client.chat.completions.create(

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            model="llama-3.1-8b-instant",
        )

        raw = (

            chat_completion
            .choices[0]
            .message
            .content
        )

        return jsonify({
            "summary": raw,
            "raw_content": raw
        })

    except Exception as e:

        return jsonify({"error": str(e)}), 500

# LIVE QUIZ API
@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():

    data = request.json

    topic = data.get("topic", "").strip()

    content = data.get("content", "").strip()

    if not topic or not content:

        return jsonify({"error": "No topic or content provided"}), 400

    prompt = f"""

You are Brain Byte AI, a smart quiz generator.

Generate as many quiz questions as possible based on this content about {topic}.

Mix these types (use each at least once):
- MCQ (multiple choice, 4 options)
- True/False
- Fill in the blank (use ___ for blank)

STRICT FORMAT:

TYPE: MCQ
Q: Question here?
A. Option 1
B. Option 2
C. Option 3
D. Option 4
ANSWER: A

TYPE: TF
Q: Statement here.
ANSWER: True

TYPE: FIB
Q: The ___ is the powerhouse of the cell.
ANSWER: mitochondria

RULES:
- Generate as many questions as possible
- Mix all 3 types, use each at least once
- Base questions ONLY on provided content
- No explanations
- No extra text

CONTENT:
{content[:4000]}

"""

    try:

        chat_completion = client.chat.completions.create(

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            model="llama-3.1-8b-instant"
        )

        raw = (

            chat_completion
            .choices[0]
            .message
            .content
        )

        # PARSE QUESTIONS
        questions = []

        blocks = raw.strip().split("TYPE:")

        for block in blocks:

            block = block.strip()

            if not block:
                continue

            lines = [l.strip() for l in block.split("\n") if l.strip()]

            if not lines:
                continue

            qtype = lines[0].strip()

            question = ""
            options = []
            answer = ""

            for line in lines[1:]:

                if line.startswith("Q:"):
                    question = line.replace("Q:", "").strip()

                elif (
                    line.startswith("A.")
                    or line.startswith("B.")
                    or line.startswith("C.")
                    or line.startswith("D.")
                ):
                    options.append(line)

                elif line.startswith("ANSWER:"):
                    answer = line.replace("ANSWER:", "").strip()

            if question and answer:

                questions.append({
                    "type": qtype,
                    "question": question,
                    "options": options,
                    "answer": answer
                })

        return jsonify({"questions": questions})

    except Exception as e:

        return jsonify({"error": str(e)}), 500

# QUIZ PAGE — UPDATED FOR 10 QUESTIONS PER DIFFICULTY
@app.route("/quiz/<filename>")
def quiz(filename):

    filepath = os.path.join(

        app.config["UPLOAD_FOLDER"],

        filename
    )

    text = ""

    reader = PdfReader(filepath)

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            text += page_text + " "

    cleaned_text = clean_pdf_text(text)

    chunks = chunk_text(

        cleaned_text,

        max_words=1200
    )

    easy_questions = []
    moderate_questions = []
    difficult_questions = []

    try:

        for chunk in chunks:

            # UPDATED PROMPT: Request 10 questions per difficulty level
            prompt = f"""

Generate quiz questions from the study material.

Create 3 separate difficulty levels with 10 questions each:

1. EASY — 10 questions
2. MODERATE — 10 questions  
3. DIFFICULT — 10 questions

FORMAT FOR EACH:

LEVEL: EASY
TOPIC: AI
Q: What is Artificial Intelligence?
A. Simulation of human intelligence
B. Type of database
C. Hardware device
D. Network cable
ANSWER: A

RULES:
1. Generate EXACTLY 10 questions per difficulty level (30 total)
2. Include LEVEL tag for each
3. Include TOPIC tag
4. No explanations or extra text
5. All questions must be valid MCQ with 4 options

CONTENT:
{chunk}

"""

            chat_completion = client.chat.completions.create(

                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],

                model="llama-3.1-8b-instant",
            )

            result = (

                chat_completion
                .choices[0]
                .message
                .content
            )

            blocks = result.split("Q:")

            for block in blocks:

                block = block.strip()

                if not block:
                    continue

                lines = block.split("\n")

                question = lines[0].strip()

                options = []
                correct_answer = ""
                topic = "General"
                level = "MODERATE"

                for line in lines[1:]:

                    line = line.strip()

                    if line.startswith("LEVEL:"):
                        level = line.replace("LEVEL:","").strip().upper()

                    elif line.startswith("TOPIC:"):
                        topic = line.replace("TOPIC:","").strip()

                    elif (
                        line.startswith("A.")
                        or line.startswith("B.")
                        or line.startswith("C.")
                        or line.startswith("D.")
                    ):
                        options.append(line)

                    elif line.startswith("ANSWER:"):
                        correct_answer = line.replace("ANSWER:","").strip()

                if question and len(options) == 4:

                    question_data = {
                        "level": level,
                        "topic": topic,
                        "question": question,
                        "options": options,
                        "answer": correct_answer
                    }

                    if level == "EASY":
                        easy_questions.append(question_data)
                    elif level == "MODERATE":
                        moderate_questions.append(question_data)
                    elif level == "DIFFICULT":
                        difficult_questions.append(question_data)

    except Exception as e:

        print(e)

    return render_template(

        "quiz.html",

        easy_quiz=easy_questions,
        moderate_quiz=moderate_questions,
        difficult_quiz=difficult_questions,
        filename=filename
    )

# AI CHAT PAGE
@app.route("/chat/<filename>")
def chat_page(filename):

    return render_template(

        "chat.html",

        filename=filename
    )

# AI CHAT API
@app.route("/ask_ai", methods=["POST"])
def ask_ai():

    data = request.json

    question = data.get("question")

    filename = data.get("filename")

    filepath = os.path.join(

        app.config["UPLOAD_FOLDER"],

        filename
    )

    text = ""

    reader = PdfReader(filepath)

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            text += page_text + " "

    cleaned_text = clean_pdf_text(text)

    limited_text = cleaned_text[:12000]

    prompt = f"""

You are an AI study assistant.

Answer ONLY using uploaded PDF.

PDF CONTENT:
{limited_text}

USER QUESTION:
{question}

RULES:
1. Answer clearly
2. Keep educational style
3. Use only PDF content
4. If answer not found say:
'Answer not found in PDF'

"""

    try:

        chat_completion = client.chat.completions.create(

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            model="llama-3.1-8b-instant"
        )

        answer = (

            chat_completion
            .choices[0]
            .message
            .content
        )

        return jsonify({"answer": answer})

    except Exception as e:

        return jsonify({"answer": str(e)})

# TEST AI
@app.route("/test_ai")
def test_ai():

    try:

        chat_completion = client.chat.completions.create(

            messages=[
                {
                    "role": "user",
                    "content": "Say Hello",
                }
            ],

            model="llama-3.1-8b-instant",
        )

        return (

            chat_completion
            .choices[0]
            .message
            .content
        )

    except Exception as e:

        return str(e)

# RUN APP
if __name__ == "__main__":

    app.run(debug=True)
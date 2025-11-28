import os
from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv
import openai
import pdfplumber
from fpdf import FPDF
from docx import Document
from wordcloud import WordCloud

# Load .env file
load_dotenv()

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'resumes'
app.config['STATIC_RESUME_FOLDER'] = 'static/resumes'

# Set OpenAI API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_RESUME_FOLDER'], exist_ok=True)

# Extract text from PDF/DOCX
def extract_text(file_path):
    if file_path.endswith('.pdf'):
        text = ''
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + '\n'
        return text
    elif file_path.endswith('.docx'):
        doc = Document(file_path)
        return '\n'.join([p.text for p in doc.paragraphs])
    else:
        return ''

# AI-powered resume analysis
def analyze_resume(resume_text, job_title, job_desc):
    prompt = f"""
    You are an expert career counselor. Analyze the resume below.

    Resume: {resume_text}

    Job Title: {job_title}
    Job Description: {job_desc}

    Provide:
    1. ATS Score (0-100)
    2. Sequence check of sections (is it ATS-friendly?)
    3. Mistakes and formatting issues
    4. Suggestions to improve resume
    5. Skills to learn for this job
    6. Job profiles suitable for this resume
    """
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=700
    )
    return response.choices[0].text

# Generate improved PDF
def generate_pdf(resume_text, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in resume_text.split('\n'):
        pdf.multi_cell(0, 10, line)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    pdf.output(file_path)
    return file_path

# Generate skill cloud image
def generate_skill_cloud(resume_text, filename):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(resume_text)
    cloud_path = os.path.join(app.config['STATIC_RESUME_FOLDER'], filename)
    wordcloud.to_file(cloud_path)
    return cloud_path

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Upload resume
        resume_file = request.files['resume']
        job_title = request.form['job_title']
        job_desc = request.form['job_desc']

        # Save uploaded file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_file.filename)
        resume_file.save(file_path)

        # Extract text
        resume_text = extract_text(file_path)

        # AI analysis
        analysis = analyze_resume(resume_text, job_title, job_desc)

        # Generate improved PDF
        improved_pdf_filename = "improved_resume.pdf"
        generate_pdf(resume_text, improved_pdf_filename)

        # Generate skill cloud
        cloud_filename = "skill_cloud.png"
        generate_skill_cloud(resume_text, cloud_filename)

        return render_template(
            'result.html',
            analysis=analysis,
            pdf_file=improved_pdf_filename,
            cloud_img=cloud_filename
        )
    return render_template("index.html")

@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return "File not found!", 404
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)

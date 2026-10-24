
# AIVOA.AI - AI-Powered Deviation Intake Module

An AI-assisted deviation intake application developed for the AIVOA.AI AI Product Engineer internship assessment.

The application helps pharmaceutical manufacturing teams transform unstructured deviation reports, emails, and documents into structured records using AI-assisted extraction and human review.

## Problem Statement

Documenting pharmaceutical manufacturing deviations can involve collecting information from multiple sources, identifying relevant details, assessing potential impact, and recording the information consistently.

This project aims to simplify that workflow through an AI-assisted intake interface.

## Key Features

- Submit deviation information by pasting text or email content.
- Upload supported documents for analysis.
- Extract relevant deviation information using the configured AI pipeline.
- Populate the deviation form after successful analysis.
- Generate AI-assisted impact and severity recommendations.
- Review and edit extracted information before saving.
- Distinguish AI-extracted information from user-edited fields.
- Persist deviation records through the backend database service.
- Explore API endpoints using FastAPI's interactive documentation.

AI-generated information supports human review and does not replace qualified personnel or established pharmaceutical quality procedures.

## Technology Stack

### Frontend
- React 18
- Redux Toolkit
- React Redux
- Vite

### Backend
- Python
- FastAPI
- Pydantic
- SQLAlchemy

### AI
- LangGraph
- LangChain Groq integration
- Groq API

### Database
- PostgreSQL
- SQLAlchemy ORM

### Document Processing
- pypdf
- python-multipart

## Architecture

1. The user submits deviation text or a supported document through the React interface.
2. The frontend sends a request to the FastAPI backend.
3. The backend validates the input and coordinates AI processing through its service layer.
4. LangGraph and Groq process the submitted information when the real AI service is enabled.
5. The extracted information and recommendations are returned to the frontend.
6. The user reviews and edits the information.
7. The backend saves the deviation record to the configured database.

## Project Structure

```text
aivoa-deviation-intake/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── .env.example
│   └── README.md
├── .gitignore
└── README.md

```

Prerequisites

- Python compatible with the backend dependencies
- Node.js and npm
- A PostgreSQL database
- A Groq API key for real AI processing

Getting Started

1. Clone the repository

git clone https://github.com/IamFemi001/aivoa-deviation-intake.git
cd aivoa-deviation-intake

2. Configure the backend

cd backend
python -m venv .venv

Activate the virtual environment.

Linux or macOS:

source .venv/bin/activate

Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Create your local environment file:

cp .env.example .env

Configure the database connection and Groq API key in "backend/.env", following the variable names in "backend/.env.example".

Use your own credentials. Never commit actual ".env" files or publish API keys and database passwords.

3. Run the backend

From the "backend" directory:

uvicorn app.main:app --reload

Default local API address:

"http://localhost:8000"

Interactive API documentation:

"http://localhost:8000/docs"

Health endpoint:

"http://localhost:8000/api/health"

4. Configure the frontend

Open another terminal and run:

cd frontend
npm install
cp .env.example .env

Configure these local development settings in "frontend/.env":

VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://localhost:8000

5. Run the frontend

From the "frontend" directory:

npm run dev

Open the local URL printed by Vite. The default is:

"http://localhost:5173"

Keep the backend and frontend running while testing the integrated application.

API Overview

The main analysis endpoint is:

"POST /api/deviations/analyze"

For available endpoints, request formats, response schemas, and error details, use the interactive documentation at "/docs" while the backend is running.

Build and Testing

To build the frontend for production, run this command from the "frontend" directory:

npm run build

The generated frontend build is placed in "frontend/dist/".

Automated tests and integration behaviour should be verified against the current source code before considering the application production-ready.

Security and Responsible Use

- Keep API keys and database credentials in local environment files.
- Do not commit ".env" files.
- Use ".env.example" files to document configuration without exposing secrets.
- Review AI-generated information before saving deviation records.
- Treat severity recommendations as decision support, not as a replacement for established quality procedures.
- Validate the application and its security before production deployment.

Author

Oluwafemi Michael Oyinbojuni

GitHub: "@IamFemi001" (https://github.com/IamFemi001)

Repository

"https://github.com/IamFemi001/aivoa-deviation-intake" (https://github.com/IamFemi001/aivoa-deviation-intake)

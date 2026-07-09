# CMA Indigenous Governance AI Platform

GitHub-ready Streamlit application for the CMA Indigenous Governance AI Platform.

## What this version includes

- Streamlit GUI
- Gemini API via environment variable or Streamlit secrets
- PDF, DOCX, TXT, MD document upload
- FAISS vector retrieval
- SQLite case/document/output registry
- Multi-agent workflows
- Downloadable PDF reports for each agent
- Example Amazigh Libya map

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Gemini API key to `.env`:

```env
GEMINI_API_KEY=your_key_here
```

Run:

```bash
streamlit run app.py
```

## Streamlit Cloud setup

1. Push this folder to GitHub.
2. Deploy the repository on Streamlit Cloud.
3. Add this secret in Streamlit Cloud settings:

```toml
GEMINI_API_KEY = "your_key_here"
```

## Deployment

This application is being migrated from Streamlit Community Cloud to Google Cloud Run as part of the Indigenous Smart Governance Platform (ISGP) architecture.

Do not commit `.env` or `.streamlit/secrets.toml` to GitHub.

import html
import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from PIL import Image

import faiss
import folium
import google.generativeai as genai
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from docx import Document
from dotenv import load_dotenv
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sentence_transformers import SentenceTransformer

# -----------------------------------------------------------------------------
# Streamlit page config must be the first Streamlit command.
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ⵣ Indigenous Smart Governance Platform ⵣ",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
load_dotenv()

DB_PATH = "cma_platform.db"
MAP_STORE = Path("maps")
REPORT_STORE = Path("reports")
ASSET_STORE = Path("assets")
BANNER_IMAGE = ASSET_STORE / "cma_banner.png"
MAP_STORE.mkdir(exist_ok=True)
REPORT_STORE.mkdir(exist_ok=True)
ASSET_STORE.mkdir(exist_ok=True)


def get_gemini_api_key() -> str | None:
    """Read Gemini key from Streamlit secrets first, then environment variables."""
    try:
        key = st.secrets.get("GEMINI_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY")

st.markdown("""
<div class="main-title">ⵣ Indigenous Smart Governance Platform ⵣ</div>
""", unsafe_allow_html=True)

def render_government_style_banner() -> None:
    """Render the 1600x200px CMA banner if available, otherwise show a text fallback."""
    if BANNER_IMAGE.exists():
        try:
            banner = Image.open(BANNER_IMAGE)
            # The banner asset is designed at 1600 x 400 px.
            st.markdown('<div class="hero-banner-card">', unsafe_allow_html=True)
            st.image(banner, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            return
        except Exception as exc:
            st.warning(f"Banner could not be loaded: {exc}")

#   st.markdown(
#        """
# <div class="main-title">ⵣ Indigenous Smart Governance Platform ⵣ</div>
# <div class="subtitle">Empowering Indigenous Peoples' Rights, Lands, Resources, Languages and Futures</div>
# """,
#        unsafe_allow_html=True,
#    )


# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { background-color: #f8fafc; }

/* Left sidebar upload panel */
section[data-testid="stSidebar"] {
    background: #eef2f7;
    border-right: 1px solid #dce3ea;
    min-width: 270px !important;
    max-width: 320px !important;
}
section[data-testid="stSidebar"] * {
    color: #1f2937 !important;
}
div[data-testid="stSidebarContent"] {
    padding-top: 1.5rem;
}
.sidebar-title {
    font-size: 21px;
    font-weight: 800;
    color: #1f2937;
    margin-bottom: 6px;
}
.sidebar-subtitle {
    font-size: 13px;
    color: #4b5563;
    margin-bottom: 12px;
}
.upload-panel {
    background: white;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 3px 12px rgba(0,0,0,0.04);
    margin-bottom: 16px;
}
.upload-limit {
    color: #6b7280 !important;
    font-size: 12px;
    margin-top: 8px;
}
.uploaded-file {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #166534 !important;
    padding: 7px 9px;
    border-radius: 8px;
    font-size: 12px;
    margin-top: 6px;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #1f2937 !important;
}

/* Main title */
.main-title {
    font-size: 34px;
    font-weight: 800;
    color: #1e88e5;
    text-align: center;
    margin-bottom: 5px;
}
.subtitle {
    font-size: 17px;
    color: #43a047;
    text-align: center;
    margin-bottom: 35px;
}

/* Inputs */
.stTextInput input,
.stTextArea textarea {
    background-color: #eaf7ec !important;
    border: 1px solid #c8e6c9 !important;
    border-radius: 8px !important;
}
.stSelectbox div[data-baseweb="select"] > div {
    background-color: #f1f3f7 !important;
    border-radius: 8px !important;
}

/* Buttons */
.stButton > button {
    background-color: #1e88e5;
    color: white !important;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    font-weight: 600;
    border: none;
}
.stButton > button:hover {
    background-color: #1565c0;
    color: white !important;
}
.stDownloadButton > button {
    background-color: #2e7d32;
    color: white !important;
    border-radius: 6px;
    font-weight: 600;
}

/* Page sections */
.card {
    background: white;
    padding: 22px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 4px 14px rgba(0,0,0,0.04);
    margin-bottom: 20px;
}
.section-title {
    font-size: 24px;
    font-weight: 700;
    color: #1f2937;
    margin-top: 30px;
    margin-bottom: 15px;
}
.small-muted {
    font-size: 13px;
    color: #6b7280;
}

/* Sidebar upload note */
.upload-box {
    background: white;
    padding: 18px;
    border-radius: 10px;
    border: 1px solid #e5e7eb;
    margin-top: 10px;
}
.upload-note {
    background: white;
    padding: 14px;
    border-radius: 10px;
    border: 1px solid #e5e7eb;
    color: #6b7280 !important;
    font-size: 13px;
}

/* Report card */
.report-card {
    background: white;
    padding: 18px;
    border-radius: 10px;
    border-left: 5px solid #43a047;
    box-shadow: 0 3px 12px rgba(0,0,0,0.05);
    margin-bottom: 15px;
}


/* Fixed visible left upload panel (not Streamlit sidebar) */
.left-upload-panel {
    background: #eef2f7;
    border: 1px solid #dce3ea;
    border-radius: 12px;
    padding: 18px 16px;
    margin-bottom: 12px;
}
.left-upload-panel h3 {
    color: #1f2937;
    font-size: 20px;
    margin: 0 0 12px 0;
    font-weight: 800;
}
.left-upload-subtitle {
    color: #4b5563;
    font-size: 13px;
    margin: 0;
}
.upload-help-box {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px;
    color: #6b7280;
    font-size: 13px;
    margin-top: 10px;
    margin-bottom: 16px;
}

/* Government-style hero banner - fits 1600x200 CMA banner */
.hero-banner-card {
    background: transparent;
    padding: 0;
    margin: 0 0 12px 0;
    border: none;
    box-shadow: none;
    overflow: hidden;
    max-width: 100%;
}

.hero-description {
    background: #ffffff;
    border-left: 5px solid #43a047;
    padding: 14px 18px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    margin-bottom: 20px;
    color: #1f2937;
    font-size: 15px;
    line-height: 1.6;
    text-align: justify;
}

</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Cached embedding model
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading embedding model...")
def get_embed_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


EMBED_MODEL = get_embed_model()

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            title TEXT,
            query TEXT,
            workflow TEXT,
            output_type TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            case_id TEXT,
            filename TEXT,
            text TEXT,
            doc_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS outputs (
            output_id TEXT PRIMARY KEY,
            case_id TEXT,
            agent_name TEXT,
            output_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Add output_type to existing databases created before this upgrade.
    existing_columns = [row[1] for row in cur.execute("PRAGMA table_info(cases)").fetchall()]
    if "output_type" not in existing_columns:
        cur.execute("ALTER TABLE cases ADD COLUMN output_type TEXT")
    conn.commit()
    conn.close()


def save_case(title: str, query: str, workflow: str, output_type: str) -> str:
    case_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cases (case_id,title,query,workflow,output_type,status) VALUES (?,?,?,?,?,?)",
        (case_id, title, query, workflow, output_type, "running"),
    )
    conn.commit()
    conn.close()
    return case_id


def update_case_status(case_id: str, status: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE cases SET status=? WHERE case_id=?", (status, case_id))
    conn.commit()
    conn.close()


def save_document(case_id: str, filename: str, text: str, doc_type: str) -> str:
    doc_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO documents (doc_id,case_id,filename,text,doc_type) VALUES (?,?,?,?,?)",
        (doc_id, case_id, filename, text, doc_type),
    )
    conn.commit()
    conn.close()
    return doc_id


def save_output(case_id: str, agent_name: str, output_json: dict) -> str:
    output_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO outputs (output_id,case_id,agent_name,output_json) VALUES (?,?,?,?)",
        (output_id, case_id, agent_name, json.dumps(output_json, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    return output_id


def query_registry() -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(DB_PATH)
    cases = pd.read_sql_query("SELECT * FROM cases ORDER BY created_at DESC", conn)
    outputs = pd.read_sql_query("SELECT * FROM outputs ORDER BY created_at DESC", conn)
    conn.close()
    return cases, outputs


init_db()

# -----------------------------------------------------------------------------
# Document extraction
# -----------------------------------------------------------------------------
def extract_text_from_file(uploaded_file) -> str:
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if filename.endswith(".docx"):
            doc = Document(uploaded_file)
            return "\n".join(p.text for p in doc.paragraphs)
        if filename.endswith((".txt", ".md")):
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        st.warning(f"Could not extract text from {uploaded_file.name}: {exc}")
    return ""


# -----------------------------------------------------------------------------
# Vector Store
# -----------------------------------------------------------------------------
class VectorStore:
    def __init__(self):
        self.chunks: list[dict] = []
        self.index = None

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
        words = text.split()
        chunks = []
        start = 0
        step = max(1, chunk_size - overlap)
        while start < len(words):
            chunks.append(" ".join(words[start : start + chunk_size]))
            start += step
        return chunks

    def rebuild(self) -> None:
        self.chunks = []
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT doc_id, filename, text, doc_type FROM documents").fetchall()
        conn.close()
        for doc_id, filename, text, doc_type in rows:
            for chunk in self.chunk_text(text or ""):
                if chunk.strip():
                    self.chunks.append(
                        {
                            "doc_id": doc_id,
                            "filename": filename,
                            "doc_type": doc_type,
                            "text": chunk,
                        }
                    )
        if not self.chunks:
            self.index = None
            return
        embeddings = EMBED_MODEL.encode([c["text"] for c in self.chunks])
        embeddings = np.array(embeddings).astype("float32")
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)

    def search(self, query: str, k: int = 5) -> list[dict]:
        if self.index is None or not self.chunks:
            return []
        q_emb = EMBED_MODEL.encode([query])
        q_emb = np.array(q_emb).astype("float32")
        _, indices = self.index.search(q_emb, min(k, len(self.chunks)))
        return [self.chunks[i] for i in indices[0] if 0 <= i < len(self.chunks)]


VECTOR_STORE = VectorStore()

# -----------------------------------------------------------------------------
# Gemini helpers and agents
# -----------------------------------------------------------------------------
def safe_json_response(model, prompt: str) -> dict:
    response = None
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except Exception as exc:
        raw = getattr(response, "text", "") if response is not None else ""
        print(f"JSON generation failed: {exc}\nRaw response: {raw}")
        return {
            "agent": "System",
            "summary": f"Generation failed: {exc}",
            "key_findings": [],
            "risks": [],
            "actions": [],
            "evidence": [],
            "confidence": "low",
        }



OUTPUT_STRUCTURES = {
    "Legal Dossier": {
        "purpose": "A formal evidence-based legal case dossier for lawyers, municipalities, Indigenous representatives and advocacy teams.",
        "sections": [
            "Executive Summary",
            "Background and Context",
            "Facts and Evidence Reviewed",
            "Affected Indigenous Peoples / Communities",
            "Potential UNDRIP Violations",
            "Legal Analysis",
            "Risks, Weaknesses and Evidence Gaps",
            "Recommended Legal and Advocacy Actions",
            "Annex / Evidence List",
        ],
    },
    "News Report": {
        "purpose": "A balanced journalistic news report suitable for public information and media publication.",
        "sections": [
            "Headline",
            "Lead Paragraph",
            "Background",
            "Key Developments",
            "Community Impact",
            "Relevant Rights Context",
            "Responses / Statements",
            "Conclusion",
        ],
    },
    "Press Release": {
        "purpose": "A concise media-ready press release for public communication.",
        "sections": [
            "Headline",
            "Subheading",
            "Date and Location",
            "Opening Paragraph",
            "Main Body",
            "Quote from Indigenous Representative",
            "Call to Action",
            "Contact / Notes to Editors",
        ],
    },
    "Public Statement": {
        "purpose": "A formal public statement expressing the position of Indigenous representatives or institutions.",
        "sections": [
            "Opening Position",
            "Main Concerns",
            "Rights-Based Argument",
            "Demands / Requests",
            "Call for Dialogue or Action",
            "Closing Message",
        ],
    },
    "UN Intervention": {
        "purpose": "A concise oral intervention suitable for EMRIP, UNPFII, Human Rights Council or similar mechanisms.",
        "sections": [
            "Chairperson Greeting",
            "Brief Context",
            "Key Rights Concern",
            "Relevant UNDRIP Articles",
            "Recommendations to States / UN Mechanisms",
            "Closing Statement",
        ],
    },
    "Thematic Report": {
        "purpose": "A structured thematic report analysing patterns, rights issues and recommendations.",
        "sections": [
            "Executive Summary",
            "Theme and Scope",
            "Evidence Overview",
            "Patterns and Trends",
            "Legal and Human Rights Analysis",
            "Impact on Indigenous Peoples",
            "Recommendations",
            "Conclusion",
        ],
    },
    "FPIC Assessment": {
        "purpose": "A focused assessment of Free, Prior and Informed Consent compliance.",
        "sections": [
            "Project / Policy Overview",
            "Affected Indigenous Communities",
            "Consultation Process Reviewed",
            "Free, Prior and Informed Consent Gaps",
            "UNDRIP Analysis",
            "Risk Rating",
            "Recommended Corrective Actions",
        ],
    },
    "Land Rights Case File": {
        "purpose": "A land and natural resources case file for territorial claims, resource disputes or state-corporation agreements.",
        "sections": [
            "Case Summary",
            "Territorial Background",
            "Affected Community / Peoples",
            "Land or Resource Issue",
            "State / Corporate Conduct",
            "Evidence of Harm or Risk",
            "FPIC Concerns",
            "Legal Basis",
            "Requested Remedies",
        ],
    },
    "Environmental Impact Review": {
        "purpose": "A rights-based review of environmental, climate, water, biodiversity and livelihood impacts.",
        "sections": [
            "Project Description",
            "Environmental Risks",
            "Water / Land / Biodiversity Impacts",
            "Indigenous Livelihood and Cultural Impacts",
            "Evidence Gaps",
            "Rights-Based Analysis",
            "Recommendations",
        ],
    },
}

OUTPUT_TYPE_OPTIONS = list(OUTPUT_STRUCTURES.keys())


MEDIA_OUTPUT_STRUCTURES = {
    "Short Social Media Video Script": {
        "purpose": "A 30-90 second script for TikTok, Instagram Reels, Facebook Reels or YouTube Shorts.",
        "sections": [
            "Video Title",
            "Target Audience",
            "Hook",
            "Narration Script",
            "Scene Breakdown",
            "On-Screen Text",
            "Visual Suggestions",
            "Call to Action",
            "Hashtags",
        ],
    },
    "Documentary Video Script": {
        "purpose": "A longer documentary-style advocacy video script based on the generated report.",
        "sections": [
            "Documentary Title",
            "Purpose and Audience",
            "Opening Scene",
            "Narration Script",
            "Historical / Legal Context",
            "Key Evidence and Findings",
            "Interview Questions",
            "Suggested Visuals and B-Roll",
            "Closing Message",
        ],
    },
    "YouTube Content Package": {
        "purpose": "A YouTube-ready package including script, title, description, chapters and tags.",
        "sections": [
            "YouTube Title",
            "Video Description",
            "Opening Hook",
            "Full Video Script",
            "Suggested Chapters",
            "Thumbnail Text",
            "Tags and Hashtags",
            "Call to Action",
        ],
    },
    "Advocacy Campaign Video": {
        "purpose": "A campaign-style advocacy video designed for public mobilisation and institutional pressure.",
        "sections": [
            "Campaign Video Title",
            "Campaign Objective",
            "Target Audience",
            "Key Message",
            "Narration Script",
            "Scene-by-Scene Plan",
            "Evidence to Highlight",
            "Visual Identity Suggestions",
            "Call to Action",
        ],
    },
    "Speech Video Script": {
        "purpose": "A speech-to-camera or conference-style video script for representatives and leaders.",
        "sections": [
            "Speech Title",
            "Speaker Role",
            "Opening Address",
            "Main Speech Script",
            "Key Rights References",
            "Suggested Visual Slides",
            "Speaking Notes",
            "Closing Appeal",
        ],
    },
    "AI Video Production Brief": {
        "purpose": "A production-ready brief that can be copied into tools such as VideoExpress, HeyGen, Synthesia, Runway or similar platforms.",
        "sections": [
            "Video Objective",
            "Recommended Video Type",
            "Avatar / Presenter Instructions",
            "Narration Script",
            "Scene Prompts",
            "Image / B-Roll Prompts",
            "Subtitle Text",
            "Music and Tone",
            "Export Notes",
        ],
    },
}

MEDIA_OUTPUT_OPTIONS = list(MEDIA_OUTPUT_STRUCTURES.keys())


def get_media_structure(media_type: str) -> dict:
    return MEDIA_OUTPUT_STRUCTURES.get(media_type, MEDIA_OUTPUT_STRUCTURES["Short Social Media Video Script"])


def get_media_template(media_type: str) -> str:
    structure = get_media_structure(media_type)
    sections = "\n".join(f"{idx + 1}. {section}" for idx, section in enumerate(structure["sections"]))
    return f"""
Purpose:
{structure["purpose"]}

Required sections:
{sections}
"""


def extract_report_text(report_json: dict) -> str:
    if not report_json:
        return ""
    parts = []
    title = report_json.get("title")
    summary = report_json.get("summary")
    if title:
        parts.append(f"Title: {title}")
    if summary:
        parts.append(f"Summary: {summary}")
    sections = report_json.get("sections", [])
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict):
                parts.append(f"{section.get('heading', 'Section')}: {section.get('content', '')}")
            else:
                parts.append(str(section))
    else:
        for key in ["key_findings", "risks", "actions", "evidence"]:
            value = report_json.get(key)
            if value:
                parts.append(f"{key}: {value}")
    return "\n\n".join(parts)


def generate_media_content(model, case_id: str, source_report: dict, media_type: str, target_platform: str, video_length: str) -> dict:
    source_output_type = source_report.get("output_type", "Generated Report")
    source_text = extract_report_text(source_report)
    media_template = get_media_template(media_type)
    required_sections = get_media_structure(media_type)["sections"]
    json_schema = f"""
{{
  "agent": "Media Generator Agent",
  "source_output_type": "{source_output_type}",
  "media_type": "{media_type}",
  "target_platform": "{target_platform}",
  "video_length": "{video_length}",
  "title": "",
  "summary": "",
  "sections": [
    {{"heading": "{required_sections[0]}", "content": ""}}
  ],
  "production_notes": [],
  "evidence": [],
  "confidence": "low | medium | high"
}}
"""
    prompt = f"""
You are the Media Generator Agent for the ⵣ Indigenous Smart Governance Platform ⵣ.

Your task is to transform the already-generated platform output into a professional media advocacy product.

SOURCE OUTPUT TYPE:
{source_output_type}

REQUESTED MEDIA TYPE:
{media_type}

TARGET PLATFORM:
{target_platform}

VIDEO LENGTH:
{video_length}

SOURCE REPORT CONTENT:
{source_text}

MEDIA FORMAT TO FOLLOW:
{media_template}

RULES:
- Use only the source report content as the evidence base.
- Do not invent legal facts or new allegations.
- Make the language public-facing, clear, persuasive and respectful.
- Preserve Indigenous rights framing and UNDRIP references where relevant.
- Include practical visual guidance for editors or AI video tools.
- If evidence is limited, say so clearly.
- Return valid JSON only.
- Use the exact required section headings in a "sections" list.

JSON SCHEMA TO FOLLOW:
{json_schema}
"""
    output = safe_json_response(model, prompt)
    output["agent"] = "Media Generator Agent"
    output["media_type"] = media_type
    output["source_output_type"] = source_output_type
    output["target_platform"] = target_platform
    output["video_length"] = video_length
    if "sections" not in output:
        output["sections"] = [
            {"heading": heading, "content": output.get("summary", "No information provided.") if idx == 0 else "No information provided."}
            for idx, heading in enumerate(required_sections)
        ]
    save_output(case_id, "Media Generator Agent", output)
    return output


def get_output_structure(output_type: str) -> dict:
    return OUTPUT_STRUCTURES.get(output_type, OUTPUT_STRUCTURES["Legal Dossier"])


def get_output_template(output_type: str) -> str:
    structure = get_output_structure(output_type)
    sections = "\n".join(f"{idx + 1}. {section}" for idx, section in enumerate(structure["sections"]))
    return f"""
Purpose:
{structure["purpose"]}

Required sections:
{sections}
"""


def choose_workflow_from_doc_type(doc_type: str, query: str) -> str:
    """Use the selected document type to improve automatic workflow routing."""
    normalized = doc_type.lower().strip()

    if normalized in [
        "legal / constitution",
        "law / regulation",
        "human rights report",
        "un submission",
    ]:
        return "human_rights_workflow"

    if normalized in [
        "oil & gas contract",
        "mining contract",
        "land rights document",
    ]:
        return "land_rights_workflow"

    if normalized in [
        "environmental impact assessment",
    ]:
        return "climate_risk_workflow"

    if normalized in [
        "language & culture",
    ]:
        return "language_culture_workflow"

    if normalized in [
        "women, children & youth",
    ]:
        return "women_children_youth_workflow"

    if normalized in [
        "data sovereignty / data access",
    ]:
        return "data_access_rights_workflow"

    return ManagerAgent.choose_workflow(query)



class BaseAgent:
    def __init__(self, name: str, role: str, model):
        self.name = name
        self.role = role
        self.model = model

    def run(
        self,
        case_id: str,
        query: str,
        workflow: str,
        output_type: str,
        extra_context: str = "",
    ) -> dict:
        evidence = VECTOR_STORE.search(query, k=5)
        evidence_text = "\n\n".join(
            f"Source: {e['filename']}\n{e['text']}" for e in evidence
        )
        output_template = get_output_template(output_type)
        output_structure = get_output_structure(output_type)
        required_sections = output_structure["sections"]

        if self.name == "Report Generation Agent":
            json_schema = f"""
{{
  "agent": "{self.name}",
  "output_type": "{output_type}",
  "title": "",
  "summary": "",
  "sections": [
    {{"heading": "{required_sections[0]}", "content": ""}}
  ],
  "evidence": [],
  "confidence": "low | medium | high"
}}
"""
            agent_specific_instruction = f"""
You are the final Report Generation Agent.
Your task is to combine the previous specialist agent outputs into ONE finished {output_type}.
You must follow the requested output format exactly.

{output_template}

IMPORTANT FORMAT RULES:
- Return a JSON object only.
- The JSON must include a "sections" list.
- Each item in "sections" must have "heading" and "content".
- Use the exact section headings listed in the required sections.
- Write the content in the tone appropriate to the output type.
- Do not use the generic Summary / Key Findings / Risks / Actions format for the final report.
- Cite document filenames inside the relevant section content where evidence supports a claim.
"""
        else:
            json_schema = f"""
{{
  "agent": "{self.name}",
  "output_type": "{output_type}",
  "summary": "",
  "key_findings": [],
  "risks": [],
  "actions": [],
  "evidence": [],
  "confidence": "low | medium | high"
}}
"""
            agent_specific_instruction = f"""
Your analysis supports the final requested output type: {output_type}.

Final product direction:
{output_template}

As a specialist agent, keep your own response analytical:
- Identify findings relevant to your expertise.
- Identify risks and evidence gaps.
- Recommend actions.
- Cite document filenames.
"""

        prompt = f"""
You are {self.name} for the ⵣ Indigenous Smart Governance Platform ⵣ.

ROLE:
{self.role}

WORKFLOW:
{workflow}

REQUESTED OUTPUT TYPE:
{output_type}

TASK:
{query}

RETRIEVED EVIDENCE:
{evidence_text}

EXTRA CONTEXT FROM PREVIOUS AGENTS:
{extra_context}

AGENT-SPECIFIC INSTRUCTION:
{agent_specific_instruction}

GENERAL RULES:
- Use retrieved evidence where possible.
- Do not invent facts.
- Cite document filenames.
- If evidence is missing, say so clearly.
- Produce valid JSON only.

JSON SCHEMA TO FOLLOW:
{json_schema}
"""
        output = safe_json_response(self.model, prompt)
        output["agent"] = self.name
        output["output_type"] = output_type

        # If the report agent failed to create sections, create a fallback structure
        # so the PDF still uses the selected output format.
        if self.name == "Report Generation Agent" and "sections" not in output:
            output["sections"] = [
                {
                    "heading": heading,
                    "content": output.get("summary", "No information provided.")
                    if idx == 0
                    else "No information provided."
                }
                for idx, heading in enumerate(required_sections)
            ]

        save_output(case_id, self.name, output)
        return output


def build_agents(model) -> dict[str, BaseAgent]:
    return {
        "land": BaseAgent("Land & Natural Resources Agent", "Analyze land rights, oil, gas, mining, FPIC, UNDRIP, benefit sharing, and resource sovereignty.", model),
        "human": BaseAgent("Human Rights & Rule of Law Agent", "Analyze human rights violations, equality, discrimination, accountability, and UN mechanisms.", model),
        "data": BaseAgent("AI & Data Analytics Agent", "Structure evidence, detect patterns, identify data gaps, and support data sovereignty.", model),
        "climate": BaseAgent("Nature Conservation & Climate Change Agent", "Analyze environmental harm, water, pollution, biodiversity, climate risk, and ecological justice.", model),
        "youth": BaseAgent("Women, Children & Youth Agent", "Analyze participation, education, safeguarding, empowerment, and inclusion.", model),
        "culture": BaseAgent("Language & Culture Agent", "Analyze indigenous lanaguage, Analyze Tamazight, Tifinagh, cultural rights, heritage, education, identity, and cultural survival.", model),
        "citation": BaseAgent("Legal Citation Agent", "Map findings to UNDRIP, ICCPR, ICESCR, CERD, ACHPR, and Indigenous rights standards.", model),
        "reviewer": BaseAgent("Reviewer Agent", "Review outputs for hallucinations, weak evidence, legal risk, and missing citations.", model),
        "report": BaseAgent("Report Generation Agent", "Generate polished legal briefs, UN submissions, advocacy reports, and strategic dossiers.", model),
    }


WORKFLOWS = {
    "legal_workflow": ["human", "citation", "reviewer", "report"],
    "language_culture_workflow": ["culture", "human", "citation", "reviewer", "report"],
    "land_rights_workflow": ["land", "human", "citation", "reviewer", "report"],
    "climate_risk_workflow": ["climate", "land", "human", "reviewer", "report"],
    "human_rights_workflow": ["human", "citation", "reviewer", "report"],
    "women_children_youth_workflow": ["youth", "human", "citation", "reviewer", "report"],
    "data_access_rights_workflow": ["data", "human", "land", "climate", "youth", "culture", "citation", "reviewer", "report"],
    "full_governance_workflow": ["land", "human", "data", "climate", "youth", "culture", "citation", "reviewer", "report"],
}

class ManagerAgent:
    def __init__(self, agents: dict[str, BaseAgent]):
        self.agents = agents

    @staticmethod
    def choose_workflow(query: str) -> str:
        q = query.lower()
        if any(x in q for x in ["land", "oil", "gas", "resource", "mining", "fpic"]):
            return "land_rights_workflow"
        if any(x in q for x in ["climate", "environment", "pollution", "water"]):
            return "climate_risk_workflow"
        if any(x in q for x in ["law", "rights", "violation", "court", "undrip"]):
            return "legal_workflow"
        return "full_governance_workflow"

    def run(self, case_id: str, query: str, workflow: str, output_type: str) -> list[dict]:
        results = []
        context_chain = ""
        for key in WORKFLOWS[workflow]:
            agent = self.agents[key]
            output = agent.run(case_id, query, workflow, output_type, context_chain)
            results.append(output)
            context_chain += f"\n\nOutput from {agent.name}:\n{json.dumps(output, ensure_ascii=False)}"
        return results


# -----------------------------------------------------------------------------
# PDF and map output
# -----------------------------------------------------------------------------
def _register_pdf_font() -> str:
    """Use a Unicode font if available; otherwise fall back to Helvetica."""
    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for font_path in possible_fonts:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("AppFont", font_path))
                return "AppFont"
            except Exception:
                pass
    return "Helvetica"


def create_agent_pdf_report(case_id: str, agent_json: dict, output_type: str = "Report") -> str:
    font_name = _register_pdf_font()
    agent_name = agent_json.get("agent", "Agent Report")
    safe_agent_name = re.sub(r"[^A-Za-z0-9_-]+", "_", agent_name)
    safe_output_type = re.sub(r"[^A-Za-z0-9_-]+", "_", output_type)
    pdf_path = REPORT_STORE / f"case_{case_id}_{safe_output_type}_{safe_agent_name}.pdf"

    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    story = [
        Paragraph("ⵣ Indigenous Smart Governance Platform ⵣ", styles["Title"]),
        Spacer(1, 12),
        Paragraph(html.escape(output_type), styles["Heading1"]),
        Spacer(1, 6),
        Paragraph(html.escape(agent_name), styles["Heading2"]),
        Spacer(1, 12),
    ]

    # The Report Generation Agent uses output-specific sections.
    # This is what makes Legal Dossiers, Press Releases, UN Interventions,
    # News Reports, etc. look different in the final PDF.
    if agent_name == "Report Generation Agent" and isinstance(agent_json.get("sections"), list):
        title = agent_json.get("title")
        if title:
            story.append(Paragraph(html.escape(str(title)), styles["Heading1"]))
            story.append(Spacer(1, 12))

        summary = agent_json.get("summary")
        if summary:
            story.append(Paragraph("Summary", styles["Heading2"]))
            story.append(Paragraph(html.escape(str(summary)), styles["BodyText"]))
            story.append(Spacer(1, 12))

        for section in agent_json.get("sections", []):
            heading = section.get("heading", "Section") if isinstance(section, dict) else "Section"
            content = section.get("content", "") if isinstance(section, dict) else str(section)
            story.append(Paragraph(html.escape(str(heading)), styles["Heading2"]))

            # Preserve simple line breaks in generated text.
            for paragraph in str(content).split("\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    story.append(Paragraph(html.escape(paragraph), styles["BodyText"]))
                    story.append(Spacer(1, 6))
            story.append(Spacer(1, 8))

        evidence_items = agent_json.get("evidence", [])
        if evidence_items:
            story.append(Paragraph("Evidence / Sources", styles["Heading2"]))
            if isinstance(evidence_items, list):
                for item in evidence_items:
                    story.append(Paragraph("• " + html.escape(str(item)), styles["BodyText"]))
            else:
                story.append(Paragraph(html.escape(str(evidence_items)), styles["BodyText"]))
            story.append(Spacer(1, 10))

        story.append(Paragraph("Confidence", styles["Heading2"]))
        story.append(Paragraph(html.escape(str(agent_json.get("confidence", "Not specified."))), styles["BodyText"]))
        doc.build(story)
        return str(pdf_path)

    # Specialist agents keep the analytical report format.
    story.extend(
        [
            Paragraph("Summary", styles["Heading2"]),
            Paragraph(html.escape(str(agent_json.get("summary", "No summary provided."))), styles["BodyText"]),
            Spacer(1, 12),
        ]
    )

    for key, title in [
        ("key_findings", "Key Findings"),
        ("risks", "Risks / Concerns"),
        ("actions", "Recommended Actions"),
        ("evidence", "Evidence Used"),
    ]:
        story.append(Paragraph(title, styles["Heading2"]))
        items = agent_json.get(key, [])
        if isinstance(items, list) and items:
            for item in items:
                story.append(Paragraph("• " + html.escape(str(item)), styles["BodyText"]))
        elif items:
            story.append(Paragraph(html.escape(str(items)), styles["BodyText"]))
        else:
            story.append(Paragraph("No information provided.", styles["BodyText"]))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Confidence", styles["Heading2"]))
    story.append(Paragraph(html.escape(str(agent_json.get("confidence", "Not specified."))), styles["BodyText"]))
    doc.build(story)
    return str(pdf_path)


def create_media_pdf_report(case_id: str, media_json: dict) -> str:
    font_name = _register_pdf_font()
    media_type = media_json.get("media_type", "Media Package")
    safe_media_type = re.sub(r"[^A-Za-z0-9_-]+", "_", media_type)
    pdf_path = REPORT_STORE / f"case_{case_id}_{safe_media_type}_Media_Generator_Agent.pdf"

    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    story = [
        Paragraph("ⵣ Indigenous Smart Governance Platform ⵣ", styles["Title"]),
        Spacer(1, 12),
        Paragraph(html.escape(media_type), styles["Heading1"]),
        Spacer(1, 6),
        Paragraph("Media Generator Agent", styles["Heading2"]),
        Spacer(1, 12),
    ]

    title = media_json.get("title")
    if title:
        story.append(Paragraph(html.escape(str(title)), styles["Heading1"]))
        story.append(Spacer(1, 12))

    metadata = [
        ("Source Output Type", media_json.get("source_output_type", "Not specified")),
        ("Target Platform", media_json.get("target_platform", "Not specified")),
        ("Video Length", media_json.get("video_length", "Not specified")),
    ]
    for label, value in metadata:
        story.append(Paragraph(f"<b>{html.escape(label)}:</b> {html.escape(str(value))}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    summary = media_json.get("summary")
    if summary:
        story.append(Paragraph("Summary", styles["Heading2"]))
        story.append(Paragraph(html.escape(str(summary)), styles["BodyText"]))
        story.append(Spacer(1, 12))

    for section in media_json.get("sections", []):
        heading = section.get("heading", "Section") if isinstance(section, dict) else "Section"
        content = section.get("content", "") if isinstance(section, dict) else str(section)
        story.append(Paragraph(html.escape(str(heading)), styles["Heading2"]))
        for paragraph in str(content).split("\n"):
            paragraph = paragraph.strip()
            if paragraph:
                story.append(Paragraph(html.escape(paragraph), styles["BodyText"]))
                story.append(Spacer(1, 6))
        story.append(Spacer(1, 8))

    production_notes = media_json.get("production_notes", [])
    if production_notes:
        story.append(Paragraph("Production Notes", styles["Heading2"]))
        if isinstance(production_notes, list):
            for item in production_notes:
                story.append(Paragraph("• " + html.escape(str(item)), styles["BodyText"]))
        else:
            story.append(Paragraph(html.escape(str(production_notes)), styles["BodyText"]))
        story.append(Spacer(1, 10))

    evidence_items = media_json.get("evidence", [])
    if evidence_items:
        story.append(Paragraph("Evidence / Sources", styles["Heading2"]))
        if isinstance(evidence_items, list):
            for item in evidence_items:
                story.append(Paragraph("• " + html.escape(str(item)), styles["BodyText"]))
        else:
            story.append(Paragraph(html.escape(str(evidence_items)), styles["BodyText"]))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Confidence", styles["Heading2"]))
    story.append(Paragraph(html.escape(str(media_json.get("confidence", "Not specified."))), styles["BodyText"]))
    doc.build(story)
    return str(pdf_path)


def generate_map(case_id: str) -> str:
    locations = [
        {"name": "Zuwara", "lat": 32.9333, "lon": 12.0833},
        {"name": "Nafusa Mountains", "lat": 31.9000, "lon": 11.9000},
        {"name": "Ghadames", "lat": 30.1337, "lon": 9.5007},
        {"name": "Ghat", "lat": 24.9633, "lon": 10.1800},
    ]
    m = folium.Map(location=[27.0, 17.0], zoom_start=5)
    for loc in locations:
        folium.Marker([loc["lat"], loc["lon"]], tooltip=loc["name"]).add_to(m)
    map_path = MAP_STORE / f"case_{case_id}_map.html"
    m.save(str(map_path))
    return str(map_path)


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "workflow_completed" not in st.session_state:
    st.session_state.workflow_completed = False
    st.session_state.current_case_id = None
    st.session_state.current_agent_results = []
    st.session_state.current_map_path = None
    st.session_state.current_output_type = None
    st.session_state.current_media_result = None

# -----------------------------------------------------------------------------
# API key and model setup
# -----------------------------------------------------------------------------
api_key = get_gemini_api_key()
if not api_key:
    st.error("GEMINI_API_KEY is not set. Add it as an environment variable or in Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")
agents = build_agents(model)
manager = ManagerAgent(agents)

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

# Premium government-style page banner
render_government_style_banner()

st.markdown(
    """
<div class="hero-description" style="text-align:left;">
This platform aims to support Indigenous Peoples in asserting their rights by analysing documents related to them, whether it is a state law that violates UNDRIP or an agreement between a state and a corporation to exploit land and natural resources, etc. This AI-powered web application can analyse your uploaded documents and automatically generate legal dossiers and specialist reports highlighting potential violations of UNDRIP. Specialised AI Agents generate legal dossiers and reports that you can use, for indigenous municipalities, NGOs, legal advisers, and representatives to prepare advocacy documents, dialogue papers, evidence summaries, and future legal action.
To use this application, you need to upload your documents, preferably with a copy of UNDRIP, select your preferred prompt from a ready-developed list, edit the request if needed, select the relevant workflow and document type, and then create your legal case, news report, press release, statement, intervention, or thematic report.
<br><br>
The Key Benefits of this Platform are as follows:
<ul>
<li>Automatically analyse state laws, policies, regulations and constitutional provisions
<li>Compare state actions against international Indigenous rights standards
<li>Generate legal briefs identifying areas of concern and assist in preparing litigation strategies
<li>Highlight clauses potentially conflicting with UNDRIP and identify a lack of Free, Prior and Informed Consent (FPIC) and absence of Indigenous consultation
<li>Analyse language policies, assess compliance with linguistic rights, and generate recommendations for language revitalisation and traditional knowledge preservation
<li>Analyse impacts of natural resources and mineral projects on Women, children, and youth, producing specialised reports, and identifying disproportionate impacts
<li>Generate evidence-based recommendations, assisting IPs in defending collective rights, such as land ownership or generate evidence for environmental complaints
<li>Support IPs by reviewing legislation, drafting local policies, preparing governance reports, monitoring development projects exploiting natural resources, and supporting their decision-making process
<li>Maintain Indigenous ownership of data and sensitive information, reduce dependence on external consultants, and build institutional memory
<li>Generate submissions for UN EMRIP, UNPFII, HR Council, and Special Rapporteurs
<li>Produce thematic reports, press releases, statements and interventions
<li>Visualise Indigenous territories and create evidence maps for advocacy
<li>Provide support for engagement with governments, corporations, and international organisations, generating dialogue, negotiation briefs, and partnership proposals
<li>Save cost and time. Tasks that normally require lawyers, researchers, environmental experts, and policy analysts can be completed in minutes rather than weeks or months, offering potential savings in terms of lowering legal preparation costs and faster response to emerging threats
</ul>
This platform represents an institutional Indigenous Intelligence system. The most important benefit is that the system evolves from a simple AI assistant into a permanent institutional capability:
<ul>
<li>Indigenous Knowledge Repository
<li>Governance Support System
<li>Legal Intelligence System
<li>Environmental Monitoring System
<li>UN Engagement Platform
<li>Indigenous Diplomacy Platform
</ul>
In practical terms, it becomes a digital Indigenous governance infrastructure capable of helping Indigenous Peoples protect their rights, territories, resources, languages, institutions and future generations using evidence-based analysis aligned with UNDRIP and international law.
<br><br>
Developed by the AI Tech Academy
</div>
</div>
""",
    unsafe_allow_html=True,
)

# IMPORTANT:
# We use a real left-hand page column for Document Upload instead of st.sidebar.
# This guarantees the upload section is always visible on Streamlit Cloud, even if
# the Streamlit sidebar is collapsed or hidden by the browser layout.
left_panel, main_panel = st.columns([0.95, 5.05], gap="large")

with left_panel:
    st.markdown(
        """
<div class="left-upload-panel">
    <h3>Document Upload</h3>
    <p class="left-upload-subtitle">Upload evidence files</p>
</div>
""",
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload evidence files",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Upload PDF, DOCX, TXT or MD evidence files for the agents to analyse.",
    )

    st.markdown(
        """
<div class="upload-help-box">
    <b>200MB per file</b><br>
    PDF, DOCX, TXT, MD
</div>
""",
        unsafe_allow_html=True,
)

    if uploaded_files:
        st.markdown("**Uploaded files**")
        for uploaded_file in uploaded_files:
            size_mb = uploaded_file.size / (1024 * 1024)
            safe_name = html.escape(uploaded_file.name)
            st.markdown(
                f'<div class="uploaded-file">✅ {safe_name}<br>{size_mb:.2f} MB</div>',
                unsafe_allow_html=True,
            )

with main_panel:
    # Main input form
    case_title = st.text_input("Case Title", "Indigenous Rights Case")

    predefined_prompts = {
        "Select a professional consultation request": "",
        "Indigenous Language & Culture Protection": """Analyse the attached documents to assess their impact on Indigenous language, cultural identity, education, traditional knowledge, cultural heritage, and collective rights. Identify any restrictions, risks, or opportunities affecting the preservation and promotion of Indigenous languages and cultures.

Assess compliance with the United Nations Declaration on the Rights of Indigenous Peoples (UNDRIP), particularly Articles 8, 11, 13, 14, 15 and 31. Provide findings, risks, recommendations, and practical measures to strengthen Indigenous language revitalisation, cultural protection, education, and self-governance.""",
        "Indigenous Land Rights Assessment": """Analyse the attached documents to determine their implications for Indigenous Peoples' rights to lands, territories, natural resources, water, minerals, forests, and traditional use areas.

Identify potential violations of Indigenous land rights, resource governance principles, benefit-sharing obligations, and Free, Prior and Informed Consent (FPIC). Assess compliance with UNDRIP Articles 25, 26, 27, 28, 29 and 32.

Provide a detailed legal and policy analysis, identify risks, highlight evidence, and recommend actions to protect Indigenous territorial rights and natural resource interests.""",
        "Climate & Environmental Risk Assessment": """Analyse the attached documents to identify environmental, biodiversity, water, pollution, climate change, and ecological risks affecting Indigenous territories and communities.

Assess potential impacts on traditional livelihoods, food security, cultural heritage, sacred sites, and ecosystem integrity. Evaluate compliance with UNDRIP, environmental law principles, environmental impact assessment standards, and Indigenous environmental rights.

Generate a climate and environmental risk assessment, including findings, risk levels, mitigation measures, monitoring recommendations, and community protection strategies.""",
        "Indigenous Human Rights Review": """Review the attached documents to identify actual or potential violations of Indigenous Peoples' human rights, collective rights, equality rights, cultural rights, political participation rights, and rights to self-determination.

Assess compliance with UNDRIP, international human rights law, constitutional protections, and relevant regional human rights instruments. Identify discriminatory provisions, governance concerns, procedural violations, and barriers to Indigenous participation.

Produce a professional human rights assessment, including legal findings, evidence, international standards, risks, and recommendations for corrective action.""",
        "Women, Children & Youth Impact Assessment": """Analyse the attached documents to assess their implications for Indigenous women, children, youth, families, education, participation, health, safety, and social inclusion.

Identify potential positive and negative impacts, including gender equality concerns, youth participation barriers, educational challenges, cultural continuity issues, and protection needs. Assess compliance with UNDRIP, child rights principles, gender equality standards, and Indigenous participation rights.

Provide findings, risks, recommendations, and strategies to strengthen the meaningful participation and wellbeing of Indigenous women, children and youth.""",
        "Indigenous Data Sovereignty Review": """Analyse the attached documents to assess Indigenous Peoples' rights relating to information access, data governance, data sovereignty, transparency, consultation, public participation, and access to decision-making processes.

Identify restrictions on access to information, barriers to participation, weaknesses in transparency mechanisms, and risks relating to Indigenous knowledge, traditional knowledge, and community data.

Assess compliance with UNDRIP, Indigenous Data Sovereignty principles, FPIC requirements, and international transparency standards. Provide recommendations for strengthening Indigenous control over information, knowledge systems, and governance data.""",
        "Comprehensive Indigenous Governance Assessment": """Conduct a comprehensive multidisciplinary assessment of the attached documents from the perspectives of Indigenous governance, land rights, natural resources, language and culture, human rights, environmental protection, women and youth participation, and data sovereignty.

Identify legal, governance, environmental, cultural, social, economic, and institutional implications affecting Indigenous Peoples. Assess compliance with UNDRIP and other relevant international standards, paying particular attention to self-determination, FPIC, territorial rights, cultural rights, participation, environmental stewardship, and Indigenous governance institutions.

Produce an integrated governance report containing key findings, evidence, risk assessments, legal analysis, policy implications, recommendations, and strategic actions for Indigenous representatives, municipalities, NGOs, governments, and international organisations.""",
    }

    prompt_to_workflow = {
        "Indigenous Language & Culture Protection": "language_culture_workflow",
        "Indigenous Land Rights Assessment": "land_rights_workflow",
        "Climate & Environmental Risk Assessment": "climate_risk_workflow",
        "Indigenous Human Rights Review": "human_rights_workflow",
        "Women, Children & Youth Impact Assessment": "women_children_youth_workflow",
        "Indigenous Data Sovereignty Review": "data_access_rights_workflow",
        "Comprehensive Indigenous Governance Assessment": "full_governance_workflow",
    }

    if "query_text_area" not in st.session_state:
        st.session_state.query_text_area = ""

    def update_consultancy_request_from_predefined():
        selected = st.session_state.predefined_prompt_selectbox
        st.session_state.query_text_area = predefined_prompts.get(selected, "")
        if selected in prompt_to_workflow:
            st.session_state.workflow_selectbox = prompt_to_workflow[selected]

    st.selectbox(
        "Choose a professional consultation request:",
        list(predefined_prompts.keys()),
        key="predefined_prompt_selectbox",
        on_change=update_consultancy_request_from_predefined,
    )

    query = st.text_area(
        "Consultancy Request",
        key="query_text_area",
        height=160,
    )

    workflow_choice = st.selectbox(
        "Workflow",
        ["auto", "language_culture_workflow", "land_rights_workflow", "climate_risk_workflow", "human_rights_workflow", "women_children_youth_workflow", "data_access_rights_workflow", "full_governance_workflow"],
        key="workflow_selectbox",
    )

    doc_type = st.selectbox(
        "Document Type",
        [
            "General",
            "Legal / Constitution",
            "Law / Regulation",
            "Oil & Gas Contract",
            "Mining Contract",
            "Land Rights Document",
            "Environmental Impact Assessment",
            "Human Rights Report",
            "UN Submission",
            "Municipal Policy",
            "Language & Culture",
            "Women, Children & Youth",
            "Data Sovereignty / Data Access",
            "Media Article",
            "Research Report",
            "Other",
        ],
    )

    output_type = st.selectbox(
        "Output Type",
        OUTPUT_TYPE_OPTIONS,
        index=OUTPUT_TYPE_OPTIONS.index("Legal Dossier"),
        help="Choose the final product you want the platform to generate.",
    )

    run_button = st.button("Create Case, Index Documents & Run Agents")

# -----------------------------------------------------------------------------
# Workflow execution
# -----------------------------------------------------------------------------
if run_button:
    if not query.strip():
        st.error("Please enter a consultancy request.")
        st.stop()

    st.session_state.workflow_completed = False
    st.session_state.current_case_id = None
    st.session_state.current_agent_results = []
    st.session_state.current_map_path = None
    st.session_state.current_output_type = output_type
    st.session_state.current_media_result = None

    with st.spinner("Initializing case and indexing documents..."):
        case_id = save_case(case_title, query, workflow_choice, output_type)
        st.session_state.current_case_id = case_id

        if uploaded_files:
            for f in uploaded_files:
                text = extract_text_from_file(f)
                if text.strip():
                    save_document(case_id, f.name, text, doc_type)

        VECTOR_STORE.rebuild()
        st.success("Documents indexed.")

    workflow = choose_workflow_from_doc_type(doc_type, query) if workflow_choice == "auto" else workflow_choice
    st.info(f"Selected workflow: {workflow}")

    with st.spinner("Running multi-agent workflow..."):
        results = manager.run(case_id, query, workflow, output_type)
        st.session_state.current_agent_results = results
        st.success("Multi-agent workflow completed.")

    st.session_state.current_map_path = generate_map(case_id)
    update_case_status(case_id, "completed")
    st.session_state.workflow_completed = True
    st.rerun()

# -----------------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------------
if st.session_state.workflow_completed:
    st.markdown('<div class="section-title">Download Agent Reports</div>', unsafe_allow_html=True)

    for r in st.session_state.current_agent_results:
        agent_name = r.get("agent", "Agent Report")
        confidence = r.get("confidence", "Not specified")
        summary = html.escape(str(r.get("summary", ""))[:300])
        pdf_path = create_agent_pdf_report(st.session_state.current_case_id, r, r.get("output_type", "Report"))

        st.markdown(
            f"""
<div class="report-card">
<b>{html.escape(agent_name)}</b><br>
<span class="small-muted">Confidence: {html.escape(str(confidence))}</span><br><br>
{summary}...
</div>
""",
            unsafe_allow_html=True,
        )

        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                label=f"Download {agent_name} PDF",
                data=pdf_file,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                key=f"download_{agent_name}_{st.session_state.current_case_id}",
            )

    st.markdown('<div class="section-title">Create Advocacy Media Content</div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="report-card">
<b>Media Generator Agent</b><br>
<span class="small-muted">Generate a video script, documentary script, YouTube package, campaign video plan, speech video, or AI video production brief from the final report.</span>
</div>
""",
        unsafe_allow_html=True,
    )

    final_report = None
    for item in st.session_state.current_agent_results:
        if item.get("agent") == "Report Generation Agent":
            final_report = item
            break
    if final_report is None and st.session_state.current_agent_results:
        final_report = st.session_state.current_agent_results[-1]

    media_col1, media_col2, media_col3 = st.columns([2, 2, 1])
    with media_col1:
        selected_media_type = st.selectbox(
            "Media Output Type",
            MEDIA_OUTPUT_OPTIONS,
            key="media_output_type_selectbox",
        )
    with media_col2:
        selected_target_platform = st.selectbox(
            "Target Platform",
            [
                "Instagram / Facebook Reels",
                "TikTok",
                "YouTube Shorts",
                "YouTube Long Form",
                "LinkedIn",
                "Conference / Public Event",
                "UN / International Mechanism",
                "AI Video Tool such as VideoExpress / HeyGen / Synthesia",
            ],
            key="media_target_platform_selectbox",
        )
    with media_col3:
        selected_video_length = st.selectbox(
            "Length",
            ["30-60 seconds", "60-90 seconds", "3 minutes", "5-10 minutes", "10-20 minutes"],
            key="media_length_selectbox",
        )

    generate_media_button = st.button("Generate Media Advocacy Package")

    if generate_media_button:
        if not final_report:
            st.error("No final report is available to transform into media content.")
        else:
            with st.spinner("Running Media Generator Agent..."):
                media_result = generate_media_content(
                    model,
                    st.session_state.current_case_id,
                    final_report,
                    selected_media_type,
                    selected_target_platform,
                    selected_video_length,
                )
                st.session_state.current_media_result = media_result
                st.success("Media advocacy package generated.")

    if st.session_state.get("current_media_result"):
        media_result = st.session_state.current_media_result
        media_title = media_result.get("title") or media_result.get("media_type", "Media Advocacy Package")
        st.markdown(
            f"""
<div class="report-card">
<b>{html.escape(str(media_title))}</b><br>
<span class="small-muted">{html.escape(str(media_result.get('media_type', 'Media Package')))} • {html.escape(str(media_result.get('target_platform', 'Target platform not specified')))}</span><br><br>
{html.escape(str(media_result.get('summary', ''))[:300])}...
</div>
""",
            unsafe_allow_html=True,
        )
        media_pdf_path = create_media_pdf_report(st.session_state.current_case_id, media_result)
        with open(media_pdf_path, "rb") as media_pdf_file:
            st.download_button(
                label=f"Download {media_result.get('media_type', 'Media Package')} PDF",
                data=media_pdf_file,
                file_name=os.path.basename(media_pdf_path),
                mime="application/pdf",
                key=f"download_media_{st.session_state.current_case_id}",
            )

    st.info("Phase 2 AI video generation can later connect this production brief to tools such as VideoExpress, HeyGen, Synthesia or Runway. This release generates the professional script and production package first, keeping costs low and allowing human review before video rendering.")

    if st.session_state.current_map_path:
        st.markdown('<div class="section-title">Example Amazigh Libya Map</div>', unsafe_allow_html=True)
        components.html(Path(st.session_state.current_map_path).read_text(encoding="utf-8"), height=500)

st.markdown("---")

if st.button("Reset Workflow"):
    st.session_state.workflow_completed = False
    st.session_state.current_case_id = None
    st.session_state.current_agent_results = []
    st.session_state.current_map_path = None
    st.session_state.current_output_type = None
    st.session_state.current_media_result = None
    st.session_state.query_text_area = ""
    st.rerun()

st.markdown('<div class="section-title">Case Registry</div>', unsafe_allow_html=True)
cases_df, _ = query_registry()
st.dataframe(cases_df, use_container_width=True)

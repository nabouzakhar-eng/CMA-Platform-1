import html
import json
import base64
import os
import re
import sqlite3
import uuid
import time
import urllib.parse
import urllib.request
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
VIDEO_STORE = Path("videos")
ASSET_STORE = Path("assets")
BANNER_IMAGE = ASSET_STORE / "cma_banner.png"
MAP_STORE.mkdir(exist_ok=True)
REPORT_STORE.mkdir(exist_ok=True)
VIDEO_STORE.mkdir(exist_ok=True)
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
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


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
        self.embeddings = None

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
        rows = conn.execute("SELECT doc_id, case_id, filename, text, doc_type FROM documents").fetchall()
        conn.close()
        for doc_id, case_id, filename, text, doc_type in rows:
            for chunk in self.chunk_text(text or ""):
                if chunk.strip():
                    self.chunks.append(
                        {
                            "doc_id": doc_id,
                            "case_id": case_id,
                            "filename": filename,
                            "doc_type": doc_type,
                            "text": chunk,
                        }
                    )
        if not self.chunks:
            self.index = None
            self.embeddings = None
            return

        model = get_embed_model()

        embeddings = model.encode(
            [chunk["text"] for chunk in self.chunks],
            show_progress_bar=False,
        )
        
        embeddings = np.asarray(embeddings, dtype="float32")
        self.embeddings = embeddings
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)
        
    def search(self, query: str, k: int = 5, case_id: str | None = None) -> list[dict]:
        if self.embeddings is None or not self.chunks:
            return []

        model = get_embed_model()
        
        q_emb = model.encode(
            [query],
            show_progress_bar=False,
        )
        
        q_emb = np.asarray(q_emb, dtype="float32")

        # IMPORTANT: restrict retrieval to the current case when case_id is provided.
        # Without this, old Libya documents from previous cases can be retrieved for
        # a new Morocco case, causing the agents and maps to use the wrong country.
        candidate_indices = [
            i for i, chunk in enumerate(self.chunks)
            if case_id is None or chunk.get("case_id") == case_id
        ]
        if not candidate_indices:
            return []

        candidate_embeddings = self.embeddings[candidate_indices]
        distances = np.sum((candidate_embeddings - q_emb[0]) ** 2, axis=1)
        ranked_positions = np.argsort(distances)[: min(k, len(candidate_indices))]
        return [self.chunks[candidate_indices[pos]] for pos in ranked_positions]


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
    "Documentary Script": {
        "purpose": "A documentary-style advocacy script suitable for community awareness, NGO campaigns and public education.",
        "sections": [
            "Documentary Title",
            "Purpose and Target Audience",
            "Opening Scene",
            "Narration Script",
            "Historical / Legal Context",
            "Key Evidence and Findings",
            "Interview Questions",
            "Suggested Visuals and B-Roll",
            "Closing Message",
            "Call to Action",
        ],
    },
    "Advocacy Campaign Video": {
        "purpose": "A campaign video designed for public mobilisation, institutional pressure and rights-based advocacy.",
        "sections": [
            "Campaign Video Title",
            "Campaign Objective",
            "Target Audience",
            "Core Message",
            "Narration Script",
            "Scene-by-Scene Plan",
            "Evidence to Highlight",
            "Visual Identity Suggestions",
            "Call to Action",
            "Distribution Notes",
        ],
    },
    "YouTube Package": {
        "purpose": "A YouTube-ready package including title, description, chapters, script, tags and thumbnail text.",
        "sections": [
            "YouTube Title",
            "Video Description",
            "Opening Hook",
            "Full Video Script",
            "Suggested Chapters",
            "Thumbnail Text",
            "Tags and Hashtags",
            "Pinned Comment",
            "Call to Action",
        ],
    },
    "Podcast Episode": {
        "purpose": "A podcast episode package based on the generated report, suitable for interviews or narrated advocacy content.",
        "sections": [
            "Episode Title",
            "Episode Summary",
            "Host Introduction",
            "Main Talking Points",
            "Interview Questions",
            "Narration Script",
            "Expert Commentary Prompts",
            "Closing Reflection",
            "Call to Action",
        ],
    },
    "Social Media Campaign": {
        "purpose": "A multi-platform social media campaign package for public mobilisation and awareness raising.",
        "sections": [
            "Campaign Name",
            "Campaign Objective",
            "Key Message",
            "Audience Segments",
            "Instagram / Facebook Posts",
            "X / Twitter Thread",
            "LinkedIn Post",
            "Short Video Concepts",
            "Hashtags",
            "Call to Action",
        ],
    },
    "Speech Script": {
        "purpose": "A speech-to-camera, conference or UN-style script for Indigenous representatives and leaders.",
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
    "Gemini Omni / Veo Video Package": {
        "purpose": "A production-ready package specifically structured for Gemini Omni / Veo video generation or similar text-to-video tools.",
        "sections": [
            "Video Objective",
            "Recommended Format",
            "Primary Gemini Omni / Veo Prompt",
            "Scene Prompts",
            "Narration Script",
            "Subtitle Text",
            "Map / Evidence Visuals",
            "CMA Branding Instructions",
            "Negative Prompt / Safety Constraints",
            "Export Notes",
        ],
    },
}

MEDIA_OUTPUT_OPTIONS = list(MEDIA_OUTPUT_STRUCTURES.keys())


def get_media_structure(media_type: str) -> dict:
    return MEDIA_OUTPUT_STRUCTURES.get(media_type, MEDIA_OUTPUT_STRUCTURES["Gemini Omni / Veo Video Package"])


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


def build_gemini_omni_payload(media_json: dict) -> dict:
    """Create a safe, reviewable Gemini Omni / Veo request payload.

    This does not call the paid video API. It prepares the exact content a future
    video endpoint can use once billing, model access and model name are confirmed.
    """
    sections = media_json.get("sections", []) if isinstance(media_json, dict) else []
    section_map = {
        str(section.get("heading", "")).lower(): str(section.get("content", ""))
        for section in sections if isinstance(section, dict)
    }
    primary_prompt = section_map.get("primary gemini omni / veo prompt", "")
    if not primary_prompt:
        primary_prompt = media_json.get("summary", "Create an Indigenous rights advocacy video based on the provided media package.")
    return {
        "provider": "Google Gemini Omni / Veo",
        "status": "ready_for_review",
        "api_call_enabled": False,
        "model_env_var": "GEMINI_VIDEO_MODEL",
        "suggested_model_placeholder": os.getenv("GEMINI_VIDEO_MODEL", "veo-model-name-to-confirm"),
        "prompt": primary_prompt,
        "source_media_type": media_json.get("media_type", "Gemini Omni / Veo Video Package"),
        "target_platform": media_json.get("target_platform", "Not specified"),
        "video_length": media_json.get("video_length", "Not specified"),
        "notes": [
            "This payload is intentionally not sent automatically to avoid unexpected paid video-generation costs.",
            "Enable billing and confirm the correct Gemini/Veo model name before connecting the API call.",
            "Review all legal and factual claims before producing public video content.",
        ],
    }




# -----------------------------------------------------------------------------
# Veo Video Generation Agent - Phase 3
# -----------------------------------------------------------------------------
def _get_secret_or_env(name: str, default: str | None = None) -> str | None:
    """Read a setting from Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def _extract_section_content(package_json: dict, heading: str) -> str:
    sections = package_json.get("sections", []) if isinstance(package_json, dict) else []
    for section in sections:
        if not isinstance(section, dict):
            continue
        if str(section.get("heading", "")).strip().lower() == heading.strip().lower():
            return str(section.get("content", "")).strip()
    return ""


def build_veo_prompt_from_media_package(media_json: dict) -> str:
    """Build one concise Veo-ready prompt from the Indigenous Media & Advocacy package."""
    if not isinstance(media_json, dict):
        return "Create a dignified Indigenous rights advocacy video based on the provided evidence."

    prompt = _extract_section_content(media_json, "Primary Gemini Omni / Veo Prompt")
    scene_prompts = _extract_section_content(media_json, "Scene Prompts")
    narration = _extract_section_content(media_json, "Narration Script")
    subtitles = _extract_section_content(media_json, "Subtitle Text")
    branding = _extract_section_content(media_json, "CMA Branding Instructions")
    safety = _extract_section_content(media_json, "Negative Prompt / Safety Constraints")

    if not prompt:
        prompt = media_json.get("summary") or media_json.get("title") or "Create a dignified Indigenous rights advocacy video."

    parts = [
        "Create a professional, dignified Indigenous rights advocacy video.",
        f"Core prompt: {prompt}",
    ]
    if scene_prompts:
        parts.append(f"Scene plan: {scene_prompts}")
    if narration:
        parts.append(f"Narration guidance: {narration}")
    if subtitles:
        parts.append(f"Subtitle guidance: {subtitles}")
    if branding:
        parts.append(f"Branding guidance: {branding}")
    parts.append("Visual tone: serious, evidence-based, respectful, cinematic documentary style, natural light, no sensationalism.")
    parts.append("Do not invent facts, locations, community statements, violence, victims, corporate names or legal conclusions not present in the source report.")
    if safety:
        parts.append(f"Additional safety constraints: {safety}")
    return "\n\n".join(parts)


def _gemini_api_predict_long_running(api_key: str, model_name: str, prompt: str, parameters: dict) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:predictLongRunning?key={urllib.parse.quote(api_key)}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": parameters,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _vertex_predict_long_running(project_id: str, location: str, model_name: str, prompt: str, parameters: dict) -> dict:
    """Call Vertex AI publisher model predictLongRunning using Application Default Credentials.

    Streamlit Cloud setup option:
    - Add GOOGLE_CLOUD_PROJECT, VEO_LOCATION and VEO_MODEL to secrets.
    - Add GOOGLE_APPLICATION_CREDENTIALS_JSON as the full service-account JSON string.
    """
    try:
        import google.auth
        from google.auth.transport.requests import Request as GoogleAuthRequest
    except Exception as exc:
        raise RuntimeError(
            "google-auth is required for Vertex AI Veo calls. Add google-auth to requirements.txt, "
            "or use the Gemini API key mode."
        ) from exc

    service_json = _get_secret_or_env("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if service_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        cred_path = VIDEO_STORE / "google_service_account.json"
        cred_path.write_text(service_json, encoding="utf-8")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(GoogleAuthRequest())
    token = credentials.token

    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/"
        f"projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:predictLongRunning"
    )
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": parameters,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _poll_long_running_operation(operation: dict, api_mode: str, api_key: str | None, location: str | None, timeout_seconds: int = 900, poll_interval: int = 12) -> dict:
    operation_name = operation.get("name")
    if not operation_name:
        return operation

    start = time.time()
    last_payload = operation
    while time.time() - start < timeout_seconds:
        if api_mode == "vertex":
            try:
                import google.auth
                from google.auth.transport.requests import Request as GoogleAuthRequest
            except Exception as exc:
                raise RuntimeError("google-auth is required to poll Vertex AI operations.") from exc
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(GoogleAuthRequest())
            token = credentials.token
            op_url = f"https://{location}-aiplatform.googleapis.com/v1/{operation_name}"
            req = urllib.request.Request(op_url, headers={"Authorization": f"Bearer {token}"}, method="GET")
        else:
            op_name = operation_name
            if op_name.startswith("operations/"):
                op_url = f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={urllib.parse.quote(api_key or '')}"
            else:
                op_url = f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={urllib.parse.quote(api_key or '')}"
            req = urllib.request.Request(op_url, method="GET")

        with urllib.request.urlopen(req, timeout=90) as resp:
            last_payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        if last_payload.get("done"):
            return last_payload
        time.sleep(poll_interval)
    return {"done": False, "name": operation_name, "last_payload": last_payload, "error": "Timed out while waiting for Veo video generation."}


def _find_base64_video(obj) -> str | None:
    """Search flexibly for base64 video bytes in Gemini/Veo operation responses."""
    if isinstance(obj, dict):
        for key in ["bytesBase64Encoded", "videoBytes", "bytes_base64_encoded"]:
            value = obj.get(key)
            if isinstance(value, str) and len(value) > 100:
                return value
        for value in obj.values():
            found = _find_base64_video(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_base64_video(item)
            if found:
                return found
    return None


def generate_veo_video(case_id: str, media_json: dict, api_mode: str, model_name: str, duration_seconds: int, aspect_ratio: str, response_count: int = 1) -> dict:
    """Dedicated Veo Video Generation Agent.

    The agent runs after the Indigenous Media & Advocacy Agent. It uses the generated
    media package as the source of truth, sends a concise prompt to Veo, polls the
    long-running operation, and saves an MP4 file if video bytes are returned.
    """
    prompt = build_veo_prompt_from_media_package(media_json)
    parameters = {
        "sampleCount": int(response_count),
        "durationSeconds": int(duration_seconds),
        "aspectRatio": aspect_ratio,
        "personGeneration": "allow_adult",
    }

    result = {
        "agent": "Veo Video Generation Agent",
        "status": "not_started",
        "api_mode": api_mode,
        "model_name": model_name,
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio,
        "prompt_used": prompt,
        "operation": None,
        "video_path": None,
        "error": None,
    }

    try:
        if api_mode == "vertex":
            project_id = _get_secret_or_env("GOOGLE_CLOUD_PROJECT") or _get_secret_or_env("GCP_PROJECT_ID")
            location = _get_secret_or_env("VEO_LOCATION", "us-central1")
            if not project_id:
                raise RuntimeError("Set GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID in Streamlit secrets for Vertex AI Veo.")
            operation = _vertex_predict_long_running(project_id, location, model_name, prompt, parameters)
            final_operation = _poll_long_running_operation(operation, "vertex", None, location)
        else:
            api_key = get_gemini_api_key()
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is required for Gemini API Veo mode.")
            operation = _gemini_api_predict_long_running(api_key, model_name, prompt, parameters)
            final_operation = _poll_long_running_operation(operation, "gemini_api", api_key, None)

        result["operation"] = final_operation
        if final_operation.get("error"):
            result["status"] = "failed"
            result["error"] = json.dumps(final_operation.get("error"), ensure_ascii=False)
        else:
            b64_video = _find_base64_video(final_operation)
            if b64_video:
                video_path = VIDEO_STORE / f"case_{case_id}_veo_video.mp4"
                video_path.write_bytes(base64.b64decode(b64_video))
                result["status"] = "completed"
                result["video_path"] = str(video_path)
            else:
                result["status"] = "completed_no_inline_video"
                result["error"] = "Veo operation completed, but no inline base64 video bytes were found. Check the operation response or configure OUTPUT_STORAGE_URI/GCS output."
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)

    save_output(case_id, "Veo Video Generation Agent", result)
    return result

def generate_media_content(model, case_id: str, source_report: dict, media_type: str, target_platform: str, video_length: str, audience: str = "Indigenous Peoples, NGOs, municipalities, UN mechanisms and public audiences", language: str = "English") -> dict:
    source_output_type = source_report.get("output_type", "Generated Report")
    source_text = extract_report_text(source_report)
    media_template = get_media_template(media_type)
    required_sections = get_media_structure(media_type)["sections"]
    is_omni_package = media_type == "Gemini Omni / Veo Video Package"
    json_schema = f"""
{{
  "agent": "Indigenous Media & Advocacy Agent",
  "source_output_type": "{source_output_type}",
  "media_type": "{media_type}",
  "target_platform": "{target_platform}",
  "video_length": "{video_length}",
  "audience": "{audience}",
  "language": "{language}",
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
    omni_rules = """
SPECIAL GEMINI OMNI / VEO RULES:
- Create a clean, copy-ready text-to-video prompt suitable for Gemini Omni / Veo.
- Include scene prompts with visual style, camera movement, map/evidence visuals, narration, subtitles and branding.
- Include negative prompt/safety constraints: no fabricated violence, no exaggerated legal claims, no misleading maps, no invented community statements.
- The video should be dignified, rights-based, evidence-led and suitable for Indigenous advocacy.
""" if is_omni_package else ""
    prompt = f"""
You are the Indigenous Media & Advocacy Agent for the ⵣ Indigenous Smart Governance Platform ⵣ.

Your task is to transform the already-generated platform output into a professional Indigenous rights media and advocacy product.

SOURCE OUTPUT TYPE:
{source_output_type}

REQUESTED MEDIA TYPE:
{media_type}

TARGET PLATFORM:
{target_platform}

VIDEO LENGTH:
{video_length}

TARGET AUDIENCE:
{audience}

LANGUAGE:
{language}

SOURCE REPORT CONTENT:
{source_text}

MEDIA FORMAT TO FOLLOW:
{media_template}

RULES:
- Use only the source report content as the evidence base.
- Do not invent legal facts, community testimonies, locations, harms or allegations.
- Make the language public-facing, clear, persuasive, respectful and legally careful.
- Preserve Indigenous rights framing, FPIC, UNDRIP and self-determination where relevant.
- Include practical visual guidance for editors, designers or AI video tools.
- If evidence is limited, say so clearly.
- Return valid JSON only.
- Use the exact required section headings in a "sections" list.
- Avoid defamatory language; use "potential", "alleged", "reported", or "requires further verification" where appropriate.
{omni_rules}

JSON SCHEMA TO FOLLOW:
{json_schema}
"""
    output = safe_json_response(model, prompt)
    output["agent"] = "Indigenous Media & Advocacy Agent"
    output["media_type"] = media_type
    output["source_output_type"] = source_output_type
    output["target_platform"] = target_platform
    output["video_length"] = video_length
    output["audience"] = audience
    output["language"] = language
    if "sections" not in output:
        output["sections"] = [
            {"heading": heading, "content": output.get("summary", "No information provided.") if idx == 0 else "No information provided."}
            for idx, heading in enumerate(required_sections)
        ]
    if is_omni_package:
        output["gemini_omni_payload"] = build_gemini_omni_payload(output)
    save_output(case_id, "Indigenous Media & Advocacy Agent", output)
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
        evidence = VECTOR_STORE.search(query, k=5, case_id=case_id)
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
    pdf_path = REPORT_STORE / f"case_{case_id}_{safe_media_type}_Indigenous_Media_Advocacy_Agent.pdf"

    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    story = [
        Paragraph("ⵣ Indigenous Smart Governance Platform ⵣ", styles["Title"]),
        Spacer(1, 12),
        Paragraph(html.escape(media_type), styles["Heading1"]),
        Spacer(1, 6),
        Paragraph("Indigenous Media & Advocacy Agent", styles["Heading2"]),
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
        ("Audience", media_json.get("audience", "Not specified")),
        ("Language", media_json.get("language", "Not specified")),
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

    gemini_payload = media_json.get("gemini_omni_payload")
    if isinstance(gemini_payload, dict):
        story.append(Paragraph("Gemini Omni / Veo Payload", styles["Heading2"]))
        for key in ["provider", "status", "api_call_enabled", "suggested_model_placeholder", "prompt"]:
            if key in gemini_payload:
                story.append(Paragraph(f"<b>{html.escape(str(key))}:</b> {html.escape(str(gemini_payload.get(key)))}", styles["BodyText"]))
                story.append(Spacer(1, 6))
        notes = gemini_payload.get("notes", [])
        if notes:
            story.append(Paragraph("Payload Notes", styles["Heading2"]))
            for item in notes:
                story.append(Paragraph("• " + html.escape(str(item)), styles["BodyText"]))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Confidence", styles["Heading2"]))
    story.append(Paragraph(html.escape(str(media_json.get("confidence", "Not specified."))), styles["BodyText"]))
    doc.build(story)
    return str(pdf_path)



def _valid_lat_lon(lat, lon) -> bool:
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        return -90 <= lat_f <= 90 and -180 <= lon_f <= 180
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Simple Location Extraction Map Intelligence - NO GEMINI REQUIRED
# -----------------------------------------------------------------------------
GEOCODE_CACHE_PATH = MAP_STORE / "geocode_cache.json"

LOCATION_GAZETTEER = {
    "Morocco": (31.7917, -7.0926, "Morocco", "country"),
    "Libya": (26.3351, 17.2283, "Libya", "country"),
    "Algeria": (28.0339, 1.6596, "Algeria", "country"),
    "Tunisia": (33.8869, 9.5375, "Tunisia", "country"),
    "Mali": (17.5707, -3.9962, "Mali", "country"),
    "Niger": (17.6078, 8.0817, "Niger", "country"),
    "Mauritania": (21.0079, -10.9408, "Mauritania", "country"),
    "Western Sahara": (24.2155, -12.8858, "Western Sahara", "territory"),
    "Tamazgha": (28.0, 3.0, "North Africa", "region"),
    "North Africa": (28.0, 3.0, "North Africa", "region"),

    # Morocco / Amazigh and mining locations
    "Rabat": (34.0209, -6.8416, "Morocco", "city"),
    "Casablanca": (33.5731, -7.5898, "Morocco", "city"),
    "Marrakech": (31.6295, -7.9811, "Morocco", "city"),
    "Agadir": (30.4278, -9.5981, "Morocco", "city"),
    "Ouarzazate": (30.9335, -6.9370, "Morocco", "city"),
    "Tinghir": (31.5147, -5.5328, "Morocco", "town"),
    "Tinerhir": (31.5147, -5.5328, "Morocco", "town"),
    "Imider": (31.3752, -5.7933, "Morocco", "mine/project site"),
    "Imiter": (31.3752, -5.7933, "Morocco", "mine/project site"),
    "Bou Azzer": (30.5147, -6.8797, "Morocco", "mine/project site"),
    "Jbel Saghro": (31.0000, -5.7500, "Morocco", "mountain/region"),
    "Jebel Saghro": (31.0000, -5.7500, "Morocco", "mountain/region"),
    "High Atlas": (31.0600, -7.9150, "Morocco", "mountain/region"),
    "Middle Atlas": (33.0000, -5.0000, "Morocco", "mountain/region"),
    "Anti-Atlas": (29.8000, -8.9000, "Morocco", "mountain/region"),
    "Rif": (35.0000, -4.0000, "Morocco", "region"),
    "Souss-Massa": (30.2751, -9.3087, "Morocco", "region"),
    "Drâa-Tafilalet": (31.1499, -5.3939, "Morocco", "region"),
    "Draa-Tafilalet": (31.1499, -5.3939, "Morocco", "region"),
    "Khouribga": (32.8860, -6.9092, "Morocco", "city/mining area"),
    "Youssoufia": (32.2463, -8.5294, "Morocco", "city/mining area"),
    "Safi": (32.2994, -9.2372, "Morocco", "city/industrial area"),
    "Jerada": (34.3100, -2.1600, "Morocco", "city/mining area"),
    "Tiznit": (29.6974, -9.7316, "Morocco", "city"),
    "Guelmim": (28.9870, -10.0574, "Morocco", "city"),
    "Errachidia": (31.9314, -4.4244, "Morocco", "city"),
    "Zagora": (30.3324, -5.8384, "Morocco", "city"),
    "Taroudant": (30.4727, -8.8749, "Morocco", "city"),

    # Libya / Amazigh locations
    "Zuwara": (32.9333, 12.0833, "Libya", "city"),
    "Zwara": (32.9333, 12.0833, "Libya", "city"),
    "Nafusa Mountains": (31.9000, 11.9000, "Libya", "region"),
    "Jabal Nafusa": (31.9000, 11.9000, "Libya", "region"),
    "Ghadames": (30.1337, 9.5007, "Libya", "city"),
    "Ghat": (24.9633, 10.1800, "Libya", "city"),
    "Yefren": (32.0647, 12.5286, "Libya", "city"),
    "Jadu": (31.9551, 12.0290, "Libya", "city"),
    "Tripoli": (32.8872, 13.1913, "Libya", "city"),

    # Wider Amazigh / Tuareg areas
    "Kabylia": (36.5000, 4.5000, "Algeria", "region"),
    "Tizi Ouzou": (36.7118, 4.0459, "Algeria", "city"),
    "Bejaia": (36.7515, 5.0557, "Algeria", "city"),
    "Tamanrasset": (22.7850, 5.5228, "Algeria", "city"),
    "Ahaggar": (23.3000, 5.5333, "Algeria", "region"),
    "Hoggar": (23.3000, 5.5333, "Algeria", "region"),
    "Djerba": (33.8076, 10.8451, "Tunisia", "island"),
    "Matmata": (33.5442, 9.9711, "Tunisia", "town"),
    "Tataouine": (32.9297, 10.4518, "Tunisia", "city"),
    "Azawad": (18.0000, -1.5000, "Mali", "region"),
    "Kidal": (18.4411, 1.4078, "Mali", "city"),
    "Timbuktu": (16.7666, -3.0026, "Mali", "city"),
    "Agadez": (16.9742, 7.9865, "Niger", "city"),
    "Arlit": (18.7369, 7.3853, "Niger", "city/mining area"),
}


def _load_geocode_cache() -> dict:
    try:
        if GEOCODE_CACHE_PATH.exists():
            return json.loads(GEOCODE_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_geocode_cache(cache: dict) -> None:
    try:
        GEOCODE_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _extract_case_text(case_id: str, query: str, max_chars: int = 20000) -> str:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT filename, text FROM documents WHERE case_id=? ORDER BY created_at DESC",
        (case_id,),
    ).fetchall()
    conn.close()
    parts = [query or ""]
    for filename, text in rows:
        parts.append(f"\nSource: {filename}\n{text or ''}")
    return "\n\n".join(parts)[:max_chars]


def _extract_coordinate_locations(text: str) -> list[dict]:
    locations = []
    patterns = [
        r"(?P<lat>-?\d{1,2}\.\d+)\s*,\s*(?P<lon>-?\d{1,3}\.\d+)",
        r"lat(?:itude)?[:\s]+(?P<lat>-?\d{1,2}\.\d+)[,\s]+lon(?:gitude)?[:\s]+(?P<lon>-?\d{1,3}\.\d+)",
    ]
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            lat = match.group("lat")
            lon = match.group("lon")
            if _valid_lat_lon(lat, lon):
                key = (round(float(lat), 5), round(float(lon), 5))
                if key not in seen:
                    seen.add(key)
                    locations.append({
                        "name": f"Coordinates {lat}, {lon}",
                        "location_type": "coordinates",
                        "country": "",
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "reason": "Explicit coordinates found in the current case evidence or request.",
                        "evidence_source": "Uploaded text / user query",
                        "confidence": "high",
                    })
    return locations


def _extract_gazetteer_locations(text: str) -> list[dict]:
    locations = []
    lower_text = text.lower()
    seen = set()
    for place, (lat, lon, country, loc_type) in LOCATION_GAZETTEER.items():
        pattern = r"(?<![\wÀ-ÿ])" + re.escape(place.lower()) + r"(?![\wÀ-ÿ])"
        if re.search(pattern, lower_text, flags=re.IGNORECASE):
            key = (place.lower(), round(float(lat), 4), round(float(lon), 4))
            if key in seen:
                continue
            seen.add(key)
            locations.append({
                "name": place,
                "location_type": loc_type,
                "country": country,
                "latitude": float(lat),
                "longitude": float(lon),
                "reason": f"'{place}' was detected in the current case evidence or user request.",
                "evidence_source": "Built-in gazetteer match",
                "confidence": "high" if loc_type != "country" else "medium",
            })
    return locations


def _extract_candidate_place_names(text: str, limit: int = 10) -> list[str]:
    stopwords = {
        "United Nations", "UNDRIP", "FPIC", "Human Rights", "Legal Dossier",
        "Indigenous Peoples", "World Amazigh Congress", "Expert Mechanism",
        "Article", "Articles", "State", "Company", "Government", "Report",
        "The", "This", "That", "Analyse", "Analyze", "Platform", "Agent",
    }
    candidates = []
    seen = set()
    connector_pattern = r"\b(?:in|near|around|at|from|within|across|territory of|region of)\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]+){0,3})"
    for match in re.finditer(connector_pattern, text):
        name = match.group(1).strip(" .,:;()[]")
        if name and name not in stopwords and name.lower() not in seen:
            seen.add(name.lower())
            candidates.append(name)

    title_pattern = r"\b([A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]+){0,3})\b"
    for match in re.finditer(title_pattern, text[:8000]):
        name = match.group(1).strip(" .,:;()[]")
        if len(name) < 3 or name in stopwords or any(ch.isdigit() for ch in name):
            continue
        if name.lower() in seen:
            continue
        if any(word in name.lower() for word in ["rights", "article", "declaration", "platform", "agent", "legal", "indigenous"]):
            continue
        seen.add(name.lower())
        candidates.append(name)
        if len(candidates) >= limit:
            break
    return candidates[:limit]


def _geocode_place_name(place_name: str) -> dict | None:
    """Optional non-Gemini geocoding through OpenStreetMap Nominatim."""
    place_name = place_name.strip()
    if not place_name or len(place_name) < 3:
        return None

    cache = _load_geocode_cache()
    cache_key = place_name.lower()
    if cache_key in cache:
        return cache[cache_key]

    try:
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            "q": place_name,
            "format": "json",
            "limit": 1,
        })
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CMA-Indigenous-Governance-Platform/1.0"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        if data:
            item = data[0]
            result = {
                "name": place_name,
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "country": item.get("display_name", "").split(",")[-1].strip(),
                "type": item.get("type", "location"),
                "source": "OpenStreetMap Nominatim",
            }
            cache[cache_key] = result
            _save_geocode_cache(cache)
            time.sleep(1)
            return result
    except Exception:
        return None
    return None


def _dedupe_locations(locations: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for loc in locations:
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        name = str(loc.get("name", "")).strip()
        if not name or not _valid_lat_lon(lat, lon):
            continue
        key = (name.lower(), round(float(lat), 3), round(float(lon), 3))
        if key in seen:
            continue
        seen.add(key)
        loc["latitude"] = float(lat)
        loc["longitude"] = float(lon)
        deduped.append(loc)
    return deduped


def generate_map_intelligence(model, case_id: str, query: str, output_type: str = "Map Intelligence") -> dict:
    """Generate case-specific map data without calling Gemini."""
    case_text = _extract_case_text(case_id, query)

    locations = []
    locations.extend(_extract_coordinate_locations(case_text))
    locations.extend(_extract_gazetteer_locations(case_text))

    # Optional generic support for locations not in the built-in gazetteer.
    existing_names = {str(loc.get("name", "")).lower() for loc in locations}
    for candidate in _extract_candidate_place_names(case_text):
        if candidate.lower() in existing_names:
            continue
        geocoded = _geocode_place_name(candidate)
        if geocoded and _valid_lat_lon(geocoded.get("lat"), geocoded.get("lon")):
            locations.append({
                "name": geocoded["name"],
                "location_type": geocoded.get("type", "location"),
                "country": geocoded.get("country", ""),
                "latitude": float(geocoded["lat"]),
                "longitude": float(geocoded["lon"]),
                "reason": f"'{candidate}' was detected as a possible location and geocoded without using Gemini.",
                "evidence_source": geocoded.get("source", "Non-Gemini geocoder"),
                "confidence": "medium",
            })

    locations = _dedupe_locations(locations)
    countries = sorted({loc.get("country", "") for loc in locations if loc.get("country")})
    regions = sorted({
        loc.get("name", "") for loc in locations
        if str(loc.get("location_type", "")).lower() in ["region", "mountain/region", "territory"]
    })

    if locations:
        avg_lat = sum(loc["latitude"] for loc in locations) / len(locations)
        avg_lon = sum(loc["longitude"] for loc in locations) / len(locations)
        zoom = 5 if len(locations) > 3 else 6
        summary = f"Map generated from {len(locations)} location(s) extracted from the current case evidence without using Gemini."
        confidence = "medium"
    else:
        avg_lat, avg_lon, zoom = 20.0, 0.0, 2
        summary = "No reliable mappable locations were identified from the current case evidence. A neutral world view is shown instead of a fixed Libya fallback."
        confidence = "low"

    output = {
        "agent": "Map Intelligence Agent",
        "summary": summary,
        "countries": countries,
        "regions": regions,
        "locations": locations,
        "map_center": {"latitude": avg_lat, "longitude": avg_lon, "zoom": zoom},
        "evidence": [loc.get("evidence_source", "") for loc in locations if loc.get("evidence_source")],
        "confidence": confidence,
        "method": "simple_location_extraction_no_gemini",
    }
    save_output(case_id, "Map Intelligence Agent", output)
    return output


def generate_map(case_id: str, map_data: dict | None = None) -> str:
    """Generate a dynamic case-specific Folium map from Map Intelligence Agent JSON."""
    map_data = map_data or {}
    locations = map_data.get("locations", []) if isinstance(map_data, dict) else []
    center = map_data.get("map_center", {}) if isinstance(map_data, dict) else {}

    if locations:
        start = [
            float(center.get("latitude", locations[0].get("latitude", 20.0))),
            float(center.get("longitude", locations[0].get("longitude", 0.0))),
        ]
        zoom = int(center.get("zoom", 6))
    else:
        start = [20.0, 0.0]
        zoom = 2

    m = folium.Map(location=start, zoom_start=zoom)

    if locations:
        for loc in locations:
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            if not _valid_lat_lon(lat, lon):
                continue
            name = html.escape(str(loc.get("name", "Mapped location")))
            loc_type = html.escape(str(loc.get("location_type", "location")))
            country = html.escape(str(loc.get("country", "")))
            reason = html.escape(str(loc.get("reason", "")))
            confidence = html.escape(str(loc.get("confidence", "not specified")))
            source = html.escape(str(loc.get("evidence_source", "")))
            popup = f"""
            <b>{name}</b><br>
            Type: {loc_type}<br>
            Country: {country}<br>
            Confidence: {confidence}<br>
            Source: {source}<br>
            <br>{reason}
            """
            folium.Marker(
                [float(lat), float(lon)],
                tooltip=name,
                popup=folium.Popup(popup, max_width=320),
            ).add_to(m)
    else:
        folium.Marker(
            start,
            tooltip="No precise case locations identified",
            popup="No reliable mappable locations were identified from the uploaded evidence.",
        ).add_to(m)

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
    st.session_state.current_map_data = None
    st.session_state.current_veo_result = None

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
An AI-powered governance, legal and advocacy platform designed to support Indigenous Peoples, municipalities, NGOs and representative institutions in protecting their rights, territories, natural resources, languages and future generations. The platform analyses documents, identifies potential violations of UNDRIP and international law, and generates legal, policy and advocacy outputs in minutes.
</div>
""",
    unsafe_allow_html=True,
)
st.markdown(
    """
<h2 style="font-size:28px; font-weight:700; color:black;">
Key Capabilities:
</h2>
""",
    unsafe_allow_html=True,
)
st.markdown("""
<ul style="
font-size:18px;
color:black;
line-height:1.8;
text-align:left;
">
<li>Analyse laws, policies, regulations and agreements
<li>Identify potential violations of UNDRIP and FPIC
<li>Review mining, oil, gas and infrastructure contracts
<li>Generate legal dossiers and evidence summaries
<li>Produce UN submissions and intervention statements
<li>Generate press releases, thematic reports and advocacy materials
<li>Support Indigenous governance and decision-making
<li>Create media content for campaigns and public awareness
</ul>
""",
unsafe_allow_html=True,
)
st.markdown(
    """
<h2 style="font-size:28px; font-weight:700; color:black;">
How to Use the Platform:
</h2>
""",
    unsafe_allow_html=True,
)
st.markdown("""
<ul style="
font-size:18px;
color:black;
line-height:1.8;
text-align:left;
">
<li>Upload your documents
<li>Select a consultancy request
<li>Choose the relevant workflow
<li>Select the desired output type
<li>Generate your report
<li>Download reports and advocacy materials
</ul>
This platform represents an institutional Indigenous Intelligence system. The most important benefit is that the system evolves from a simple AI assistant into a permanent institutional capability:
""", unsafe_allow_html=True)
st.markdown(
    """
<h2 style="font-size:28px; font-weight:700; color:black;">
Key Benefits:
</h2>
""",
    unsafe_allow_html=True,
)
st.markdown("""
<ul style="
font-size:18px;
colour: black;
line-height:1.8;
text-align: left;
">
<li>Faster legal and policy analysis
<li>Reduced dependence on external consultants
<li>Lower advocacy preparation costs
<li>Stronger evidence-based decision making
<li>Enhanced UN and international engagement
<li>Protection of Indigenous knowledge and data sovereignty
<li>Institutional memory and governance continuity
</ul>
<p style="
font-size:18px;
color:black;
line-height:1.8;
text-align:left;
">
This platform is more than an AI assistant. It is designed as a permanent Indigenous Governance Infrastructure comprising:
</p>
""", unsafe_allow_html=True)
st.markdown("""
<ul style="
font-size:18px;
colour: black;
line-height:1.8;
text-align: left;
">
<li>Indigenous Knowledge Repository
<li>Legal Intelligence System
<li>Governance Support System
<li>Environmental Monitoring System
<li>UN Engagement Platform
<li>Indigenous Diplomacy Platform
</ul>
""", 
    unsafe_allow_html=True)
st.markdown(
    """
<h2 style="font-size:28px; font-weight:700; color:black;">
Advocacy & Media Studio, where users can automatically generate:
</h2>
""", 
    unsafe_allow_html=True)
st.markdown("""
<ul style="
font-size:18px;
colour: black;
line-height:1.8;
text-align: left;
">
<li>Video Scripts
<li>Documentary Scripts
<li>Podcast Episodes
<li>YouTube Packages
<li>Social Media Campaigns
<li>Public Statements
</ul>
<p style="
font-size:18px;
color:black;
line-height:1.8;
text-align:left;
">
from any report generated by the platform.
<br><br>
Together, these capabilities support Indigenous Peoples in protecting their rights, territories, natural resources, languages, institutions and future generations through evidence-based analysis aligned with UNDRIP and international law.
<br><br>
In practical terms, it becomes a digital Indigenous governance infrastructure capable of helping Indigenous Peoples protect their rights, territories, resources, languages, institutions and future generations using evidence-based analysis aligned with UNDRIP and international law.
<br><br>
Developed by the World Amazigh Congress (CMA) in collaboration with AI Tech Academy.
""", unsafe_allow_html=True)



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
    st.session_state.current_map_data = None
    st.session_state.current_veo_result = None

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

    with st.spinner("Running Map Intelligence Agent..."):
        map_data = generate_map_intelligence(model, case_id, query, output_type)
        st.session_state.current_map_data = map_data
        st.session_state.current_map_path = generate_map(case_id, map_data)
        mapped_count = len(map_data.get("locations", [])) if isinstance(map_data, dict) else 0
        st.success(f"Map generated with {mapped_count} case-specific location(s).")

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

    st.markdown('<div class="section-title">Indigenous Media & Advocacy Agent</div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="report-card">
<b>Indigenous Media & Advocacy Agent</b><br>
<span class="small-muted">Transform the final report into public-facing advocacy content, including Documentary Scripts, Advocacy Campaign Videos, YouTube Packages, Podcast Episodes, Social Media Campaigns, Speech Scripts, and Gemini Omni / Veo Video Packages.</span>
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
            index=MEDIA_OUTPUT_OPTIONS.index("Gemini Omni / Veo Video Package") if "Gemini Omni / Veo Video Package" in MEDIA_OUTPUT_OPTIONS else 0,
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
                "Podcast Platforms",
                "Conference / Public Event",
                "UN / International Mechanism",
                "Google Gemini Omni / Veo",
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

    media_col4, media_col5 = st.columns([2, 2])
    with media_col4:
        selected_audience = st.selectbox(
            "Audience",
            [
                "Indigenous communities and representatives",
                "UN experts and international mechanisms",
                "Municipalities and public authorities",
                "NGOs, donors and civil society",
                "General public and social media audiences",
                "Government and corporate dialogue partners",
            ],
            key="media_audience_selectbox",
        )
    with media_col5:
        selected_language = st.selectbox(
            "Language",
            ["English", "French", "Arabic", "Tamazight", "Bilingual English/French", "Bilingual Arabic/Tamazight"],
            key="media_language_selectbox",
        )

    if selected_media_type == "Gemini Omni / Veo Video Package":
        st.warning("This option prepares a Gemini Omni / Veo-ready production package and prompt. It does not automatically call the paid video-generation API, so it avoids unexpected costs.")

    generate_media_button = st.button("Generate Indigenous Media & Advocacy Package")

    if generate_media_button:
        if not final_report:
            st.error("No final report is available to transform into media content.")
        else:
            with st.spinner("Running Indigenous Media & Advocacy Agent..."):
                media_result = generate_media_content(
                    model,
                    st.session_state.current_case_id,
                    final_report,
                    selected_media_type,
                    selected_target_platform,
                    selected_video_length,
                    selected_audience,
                    selected_language,
                )
                st.session_state.current_media_result = media_result
                st.success("Indigenous media and advocacy package generated.")

    if st.session_state.get("current_media_result"):
        media_result = st.session_state.current_media_result
        media_title = media_result.get("title") or media_result.get("media_type", "Media Advocacy Package")
        st.markdown(
            f"""
<div class="report-card">
<b>{html.escape(str(media_title))}</b><br>
<span class="small-muted">{html.escape(str(media_result.get('media_type', 'Media Package')))} • {html.escape(str(media_result.get('target_platform', 'Target platform not specified')))} • {html.escape(str(media_result.get('language', 'Language not specified')))}</span><br><br>
{html.escape(str(media_result.get('summary', ''))[:300])}...
</div>
""",
            unsafe_allow_html=True,
        )
        if isinstance(media_result.get("gemini_omni_payload"), dict):
            payload = media_result["gemini_omni_payload"]
            st.markdown(
                f"""
<div class="report-card">
<b>Gemini Omni / Veo Payload Ready</b><br>
<span class="small-muted">Provider: {html.escape(str(payload.get('provider', 'Google Gemini Omni / Veo')))} | API call enabled: {html.escape(str(payload.get('api_call_enabled', False)))}</span><br><br>
This package includes a copy-ready prompt, scene prompts, narration, subtitles, CMA branding guidance and safety constraints for future video generation.
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

        st.markdown('<div class="section-title">Veo Video Generation Agent</div>', unsafe_allow_html=True)
        st.markdown(
            """
<div class="report-card">
<b>Veo Video Generation Agent</b><br>
<span class="small-muted">This dedicated agent runs after the Indigenous Media & Advocacy Agent. It sends the reviewed video prompt package to Google Veo and returns an MP4 video when available.</span>
</div>
""",
            unsafe_allow_html=True,
        )
        st.warning("Veo video generation is a paid Google service. Generate a video only after reviewing the media package and confirming that you accept the cost.")

        veo_col1, veo_col2, veo_col3, veo_col4 = st.columns([1.5, 2, 1, 1])
        with veo_col1:
            veo_api_mode = st.selectbox(
                "Veo API Mode",
                ["gemini_api", "vertex"],
                index=0,
                help="Use gemini_api with your Gemini API key, or vertex with Google Cloud ADC/service-account credentials.",
                key="veo_api_mode_selectbox",
            )
        with veo_col2:
            default_veo_model = os.getenv("VEO_MODEL", "veo-3.0-generate-preview")
            veo_model_name = st.text_input("Veo Model Name", default_veo_model, key="veo_model_name_input")
        with veo_col3:
            veo_duration = st.selectbox("Duration", [8, 10], index=0, key="veo_duration_selectbox")
        with veo_col4:
            veo_aspect_ratio = st.selectbox("Aspect Ratio", ["16:9", "9:16", "1:1"], index=0, key="veo_aspect_ratio_selectbox")

        confirm_veo_cost = st.checkbox(
            "I have reviewed the media package and understand that Veo video generation may incur Google Cloud / Gemini API charges.",
            key="confirm_veo_cost_checkbox",
        )
        generate_veo_button = st.button("Generate MP4 with Veo")

        if generate_veo_button:
            if not confirm_veo_cost:
                st.error("Please tick the confirmation checkbox before calling the paid Veo video API.")
            else:
                with st.spinner("Running Veo Video Generation Agent. This can take several minutes..."):
                    veo_result = generate_veo_video(
                        st.session_state.current_case_id,
                        media_result,
                        veo_api_mode,
                        veo_model_name.strip(),
                        int(veo_duration),
                        veo_aspect_ratio,
                    )
                    st.session_state.current_veo_result = veo_result
                    if veo_result.get("status") == "completed" and veo_result.get("video_path"):
                        st.success("Veo video generated successfully.")
                    else:
                        st.warning(f"Veo result: {veo_result.get('status')}. {veo_result.get('error') or ''}")

    if st.session_state.get("current_veo_result"):
        veo_result = st.session_state.current_veo_result
        st.markdown(
            f"""
<div class="report-card">
<b>Veo Video Generation Agent Result</b><br>
<span class="small-muted">Status: {html.escape(str(veo_result.get('status', 'unknown')))} | Model: {html.escape(str(veo_result.get('model_name', 'not specified')))}</span><br><br>
{html.escape(str(veo_result.get('error') or 'Video generation completed.'))}
</div>
""",
            unsafe_allow_html=True,
        )
        video_path = veo_result.get("video_path")
        if video_path and Path(video_path).exists():
            st.video(video_path)
            with open(video_path, "rb") as video_file:
                st.download_button(
                    label="Download Veo MP4 Video",
                    data=video_file,
                    file_name=os.path.basename(video_path),
                    mime="video/mp4",
                    key=f"download_veo_video_{st.session_state.current_case_id}",
                )

    st.info("Phase 3 is now prepared: the platform can generate a media package, send the reviewed prompt to Google Veo, poll the long-running operation, and return an MP4 when the API returns inline video bytes. For Vertex AI mode, configure GOOGLE_CLOUD_PROJECT, VEO_LOCATION, VEO_MODEL and GOOGLE_APPLICATION_CREDENTIALS_JSON in Streamlit secrets.")

    if st.session_state.current_map_path:
        st.markdown('<div class="section-title">Case-Specific Map Intelligence</div>', unsafe_allow_html=True)
        map_data = st.session_state.get("current_map_data") or {}
        map_summary = html.escape(str(map_data.get("summary", "Map generated from locations identified in the case evidence."))) if isinstance(map_data, dict) else "Map generated."
        st.markdown(f'<div class="report-card"><b>Map Intelligence Agent</b><br>{map_summary}</div>', unsafe_allow_html=True)
        components.html(Path(st.session_state.current_map_path).read_text(encoding="utf-8"), height=500)

st.markdown("---")

if st.button("Reset Workflow"):
    st.session_state.workflow_completed = False
    st.session_state.current_case_id = None
    st.session_state.current_agent_results = []
    st.session_state.current_map_path = None
    st.session_state.current_output_type = None
    st.session_state.current_media_result = None
    st.session_state.current_map_data = None
    st.session_state.current_veo_result = None
    st.session_state.query_text_area = ""
    st.rerun()

st.markdown('<div class="section-title">Case Registry</div>', unsafe_allow_html=True)
cases_df, _ = query_registry()
st.dataframe(cases_df, use_container_width=True)

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
    page_title="CMA Indigenous Governance AI Platform",
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
<div class="main-title">CMA Indigenous Governance AI Platform</div>
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
# <div class="main-title">CMA Indigenous Governance AI Platform</div>
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
    conn.commit()
    conn.close()


def save_case(title: str, query: str, workflow: str) -> str:
    case_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cases (case_id,title,query,workflow,status) VALUES (?,?,?,?,?)",
        (case_id, title, query, workflow, "running"),
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


class BaseAgent:
    def __init__(self, name: str, role: str, model):
        self.name = name
        self.role = role
        self.model = model

    def run(self, case_id: str, query: str, workflow: str, extra_context: str = "") -> dict:
        evidence = VECTOR_STORE.search(query, k=5)
        evidence_text = "\n\n".join(
            f"Source: {e['filename']}\n{e['text']}" for e in evidence
        )
        prompt = f"""
You are {self.name} for the CMA Indigenous Governance AI Platform.

ROLE:
{self.role}

WORKFLOW:
{workflow}

TASK:
{query}

RETRIEVED EVIDENCE:
{evidence_text}

EXTRA CONTEXT FROM PREVIOUS AGENTS:
{extra_context}

RULES:
- Use retrieved evidence where possible.
- Do not invent facts.
- Cite document filenames.
- If evidence is missing, say so clearly.
- Produce valid JSON only.

JSON SCHEMA:
{{
  "agent": "{self.name}",
  "summary": "",
  "key_findings": [],
  "risks": [],
  "actions": [],
  "evidence": [],
  "confidence": "low | medium | high"
}}
"""
        output = safe_json_response(self.model, prompt)
        output["agent"] = self.name
        save_output(case_id, self.name, output)
        return output


def build_agents(model) -> dict[str, BaseAgent]:
    return {
        "land": BaseAgent("Land & Natural Resources Agent", "Analyze land rights, oil, gas, mining, FPIC, UNDRIP, benefit sharing, and resource sovereignty.", model),
        "human": BaseAgent("Human Rights & Rule of Law Agent", "Analyze human rights violations, equality, discrimination, accountability, and UN mechanisms.", model),
        "data": BaseAgent("AI & Data Analytics Agent", "Structure evidence, detect patterns, identify data gaps, and support data sovereignty.", model),
        "climate": BaseAgent("Nature Conservation & Climate Change Agent", "Analyze environmental harm, water, pollution, biodiversity, climate risk, and ecological justice.", model),
        "youth": BaseAgent("Women, Children & Youth Agent", "Analyze participation, education, safeguarding, empowerment, and inclusion.", model),
        "culture": BaseAgent("Language & Culture Agent", "Analyze Tamazight, Tifinagh, cultural rights, heritage, education, identity, and cultural survival.", model),
        "citation": BaseAgent("Legal Citation Agent", "Map findings to UNDRIP, ICCPR, ICESCR, CERD, ACHPR, and Indigenous rights standards.", model),
        "reviewer": BaseAgent("Reviewer Agent", "Review outputs for hallucinations, weak evidence, legal risk, and missing citations.", model),
        "report": BaseAgent("Report Generation Agent", "Generate polished legal briefs, UN submissions, advocacy reports, and strategic dossiers.", model),
    }


WORKFLOWS = {
    "legal_workflow": ["human", "citation", "reviewer", "report"],
    "land_rights_workflow": ["land", "human", "citation", "reviewer", "report"],
    "climate_risk_workflow": ["climate", "land", "human", "reviewer", "report"],
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

    def run(self, case_id: str, query: str, workflow: str) -> list[dict]:
        results = []
        context_chain = ""
        for key in WORKFLOWS[workflow]:
            agent = self.agents[key]
            output = agent.run(case_id, query, workflow, context_chain)
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


def create_agent_pdf_report(case_id: str, agent_json: dict) -> str:
    font_name = _register_pdf_font()
    agent_name = agent_json.get("agent", "Agent Report")
    safe_agent_name = re.sub(r"[^A-Za-z0-9_-]+", "_", agent_name)
    pdf_path = REPORT_STORE / f"case_{case_id}_{safe_agent_name}.pdf"

    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    story = [
        Paragraph("CMA Indigenous Governance AI Platform", styles["Title"]),
        Spacer(1, 12),
        Paragraph(html.escape(agent_name), styles["Heading1"]),
        Spacer(1, 12),
        Paragraph("Summary", styles["Heading2"]),
        Paragraph(html.escape(str(agent_json.get("summary", "No summary provided."))), styles["BodyText"]),
        Spacer(1, 12),
    ]

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
st.markdown("""
<div class="hero-description">
<div class="subtitle">
This platform aims to support Indigenous Peoples in asserting their rights by analysing documents related to them, whether it is a state law that violates UNDRIP or an agreement between a state and a corporation to exploit land and natural resources, etc. This AI-powered web application can analyse your uploaded documents and automatically generate legal dossiers and specialist reports highlighting potential violations of UNDRIP. Specialised AI Agents generate legal dossiers and reports that you can use, for indigenous municipalities, NGOs, legal advisers, and representatives to prepare advocacy documents, dialogue papers, evidence summaries, and future legal action.

To use this application, you need to upload your documents, preferably with a copy of UNDRIP, select your preferred prompt from a ready-developed list, edit the request if needed, select the relevant workflow and document type, and then create your legal case, news report, press release, statement, intervention, or thematic report.
</div>

<div class="subtitle">
The Key Benefits of this Platform are as follows:
- Automatically analyse state laws, policies, regulations and constitutional provisions.
- Compare state actions against international Indigenous rights standards.
- Generate legal briefs identifying areas of concern and assist in preparing litigation strategies.
- Highlight clauses potentially conflicting with UNDRIP and identify a lack of Free, Prior and Informed Consent (FPIC) and absence of Indigenous consultation
- Analyse language policies, assess compliance with linguistic rights, and generate recommendations for language revitalisation and traditional knowledge preservation.
- Analyse impacts of natural resources and mineral projects on Women, children, and youth, producing specialised reports, and identifying disproportionate impacts.
- Generate evidence-based recommendations, assisting IPs in defending collective rights, such as land ownership or generate evidence for environmental complaints.
- Support IPs by reviewing legislation, drafting local policies, preparing governance reports, monitoring development projects exploiting natural resources, and supporting their decision-making process.
- Maintain Indigenous ownership of data and sensitive information, reduce dependence on external consultants, and build institutional memory.
- Generate submissions for UN EMRIP, UNPFII, HR Council, and Special Rapporteurs.
- Produce thematic reports, press releases, statements and interventions.
- Visualise Indigenous territories and create evidence maps for advocacy.
- Provide support for engagement with governments, corporations, and international organisations, generating dialogue, negotiation briefs, and partnership proposals.
- Save cost and time. Tasks that normally require lawyers, researchers, environmental experts, and policy analysts can be completed in minutes rather than weeks or months, offering potential savings in terms of lowering legal preparation costs and faster response to emerging threats.

This platform represents an institutional Indigenous Intelligence system. The most important benefit is that the system evolves from a simple AI assistant into a permanent institutional capability:

- Indigenous Knowledge Repository
- Governance Support System
- Legal Intelligence System
- Environmental Monitoring System
- UN Engagement Platform
- Indigenous Diplomacy Platform

In practical terms, it becomes a digital Indigenous governance infrastructure capable of helping Indigenous Peoples protect their rights, territories, resources, languages, institutions and future generations using evidence-based analysis aligned with UNDRIP and international law.

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

st.sidebar.markdown("""
    <div class="upload-box">
      <b>200MB per file</b><br>
      PDF, DOCX, TXT, MD
    </div>
""", unsafe_allow_html=True)
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
        "Select a prompt": "",
        "Analyze human rights violations in context of indigenous land rights": "Analyze human rights violations in context of indigenous land rights. Focus on forced displacement and lack of free, prior, and informed consent. Cite relevant UNDRIP articles.",
        "Assess environmental impact of mining on indigenous territories": "Assess the environmental impact of a proposed mining project on indigenous territories. Identify potential ecological harm, water contamination risks, and impact on traditional livelihoods.",
        "Examine cultural preservation efforts for endangered indigenous languages": "Examine existing efforts for the preservation of endangered indigenous languages. Discuss challenges and recommend strategies for revitalization, including education and community programs.",
        "Review legal framework for indigenous data sovereignty": "Review the legal framework for indigenous data sovereignty. Highlight gaps in current legislation and propose mechanisms to ensure indigenous control over their data.",
    }

    if "query_text_area" not in st.session_state:
        st.session_state.query_text_area = ""

    def update_consultancy_request_from_predefined():
        selected = st.session_state.predefined_prompt_selectbox
        st.session_state.query_text_area = predefined_prompts.get(selected, "")

    st.selectbox(
        "Choose a predefined consultancy request:",
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
        ["auto", "legal_workflow", "land_rights_workflow", "climate_risk_workflow", "full_governance_workflow"],
        key="workflow_selectbox",
    )

    doc_type = st.selectbox("Document Type", ["general", "legal", "environmental", "policy", "media"])

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

    with st.spinner("Initializing case and indexing documents..."):
        case_id = save_case(case_title, query, workflow_choice)
        st.session_state.current_case_id = case_id

        if uploaded_files:
            for f in uploaded_files:
                text = extract_text_from_file(f)
                if text.strip():
                    save_document(case_id, f.name, text, doc_type)

        VECTOR_STORE.rebuild()
        st.success("Documents indexed.")

    workflow = manager.choose_workflow(query) if workflow_choice == "auto" else workflow_choice
    st.info(f"Selected workflow: {workflow}")

    with st.spinner("Running multi-agent workflow..."):
        results = manager.run(case_id, query, workflow)
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
        pdf_path = create_agent_pdf_report(st.session_state.current_case_id, r)

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

    if st.session_state.current_map_path:
        st.markdown('<div class="section-title">Example Amazigh Libya Map</div>', unsafe_allow_html=True)
        components.html(Path(st.session_state.current_map_path).read_text(encoding="utf-8"), height=500)

st.markdown("---")

if st.button("Reset Workflow"):
    st.session_state.workflow_completed = False
    st.session_state.current_case_id = None
    st.session_state.current_agent_results = []
    st.session_state.current_map_path = None
    st.session_state.query_text_area = ""
    st.rerun()

st.markdown('<div class="section-title">Case Registry</div>', unsafe_allow_html=True)
cases_df, _ = query_registry()
st.dataframe(cases_df, use_container_width=True)

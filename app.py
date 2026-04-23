import streamlit as st
import os
from github_loader import load_github_repo
from rag_engine import RAGEngine

st.set_page_config(page_title="RepoChat", page_icon="", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap');
:root{--bg:#f7f5f2;--white:#ffffff;--border:#e8e4df;--accent:#2d6a4f;--accent2:#40916c;--text:#1a1a1a;--muted:#888580;--tag:#e9f5ee;--tag-text:#2d6a4f;}
*,*::before,*::after{box-sizing:border-box;}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.stApp,.main,.block-container{font-family:'DM Sans',sans-serif!important;background-color:var(--bg)!important;color:var(--text)!important;}
[data-testid="stHeader"]{background-color:var(--bg)!important;}
[data-testid="stSidebar"]{background-color:var(--white)!important;border-right:1px solid var(--border)!important;}
[data-testid="stSidebar"] *{font-family:'DM Sans',sans-serif!important;}
.stTextInput label,.stMultiSelect label,.stSlider label{font-size:11px!important;font-weight:500!important;letter-spacing:0.8px!important;text-transform:uppercase!important;color:var(--muted)!important;}
.stTextInput>div>div>input{background-color:var(--bg)!important;border:1px solid var(--border)!important;border-radius:6px!important;color:var(--text)!important;font-family:'DM Sans',sans-serif!important;font-size:13px!important;padding:8px 12px!important;}
.stTextInput>div>div>input:focus{border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(45,106,79,0.1)!important;}
.stButton>button{background-color:var(--accent)!important;color:white!important;border:none!important;border-radius:6px!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:13px!important;padding:10px 20px!important;transition:background 0.2s!important;width:100%!important;}
.stButton>button:hover{background-color:var(--accent2)!important;}
#MainMenu,footer{visibility:hidden;}
.user-bubble{background:#2d6a4f;color:white;border-radius:16px 16px 4px 16px;padding:12px 18px;margin:6px 0 6px 15%;font-size:14px;line-height:1.6;}
.bot-bubble{background:white;color:var(--text);border-radius:4px 16px 16px 16px;padding:14px 18px;margin:6px 15% 6px 0;font-size:14px;line-height:1.7;border:1px solid var(--border);box-shadow:0 1px 4px rgba(0,0,0,0.05);}
.bubble-label{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:5px;opacity:0.55;}
.source-tag{display:inline-block;background:var(--tag);color:var(--tag-text);border-radius:4px;padding:2px 8px;font-size:11px;font-weight:500;margin:2px 2px 0 0;font-family:monospace;}
.page-header{padding:2rem 0 1.2rem;border-bottom:1px solid var(--border);margin-bottom:1.5rem;}
.page-header h1{font-family:'Playfair Display',serif;font-size:1.9rem;font-weight:700;color:var(--text);letter-spacing:-0.5px;}
.page-header p{color:var(--muted);font-size:13px;margin-top:4px;font-weight:300;}
.pill-ready{background:#e9f5ee;color:#2d6a4f;border:1px solid #b7e4c7;border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600;display:inline-block;}
.pill-wait{background:#fef9ec;color:#92690e;border:1px solid #fde68a;border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600;display:inline-block;}
.empty-state{text-align:center;padding:4rem 2rem;color:var(--muted);}
.empty-state h3{font-size:15px;font-weight:500;color:var(--text);margin-bottom:6px;}
.empty-state p{font-size:13px;line-height:1.7;}
.sdiv{border:none;border-top:1px solid var(--border);margin:14px 0;}
</style>
""", unsafe_allow_html=True)

if "messages"    not in st.session_state: st.session_state.messages    = []
if "rag_engine"  not in st.session_state: st.session_state.rag_engine  = None
if "repo_loaded" not in st.session_state: st.session_state.repo_loaded = False
if "repo_url"    not in st.session_state: st.session_state.repo_url    = ""

with st.sidebar:
    st.markdown("<div style='padding:8px 0 4px'><span style='font-family:Playfair Display,serif;font-size:1.2rem;font-weight:700'>RepoChat</span></div>", unsafe_allow_html=True)
    st.markdown("<hr class='sdiv'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px;font-weight:600;letter-spacing:0.8px;text-transform:uppercase;color:#888580;margin-bottom:6px'>Configuration</p>", unsafe_allow_html=True)
    groq_key     = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    github_token = st.text_input("GitHub Token (optional)", type="password", placeholder="ghp_...")
    st.markdown("<hr class='sdiv'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px;font-weight:600;letter-spacing:0.8px;text-transform:uppercase;color:#888580;margin-bottom:6px'>Repository</p>", unsafe_allow_html=True)
    repo_url = st.text_input("Repository URL", placeholder="https://github.com/owner/repo", value=st.session_state.repo_url)
    file_extensions = st.multiselect("File types", [".py",".js",".ts",".md",".txt",".json",".yaml",".yml",".html",".css",".java",".go",".rs"], default=[".py",".md",".txt"])
    max_files = st.slider("Max files", 10, 200, 50)
    st.markdown("<br>", unsafe_allow_html=True)
    load_btn = st.button("Load Repository", use_container_width=True)
    if st.session_state.repo_loaded:
        e = st.session_state.rag_engine
        st.markdown(f'<div style="margin-top:8px"><span class="pill-ready">Indexed — {e.num_files} files</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="margin-top:8px"><span class="pill-wait">No repository loaded</span></div>', unsafe_allow_html=True)
    st.markdown("<hr class='sdiv'>", unsafe_allow_html=True)
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown("<div style='font-size:11px;color:#aaa;line-height:1.9;margin-top:8px'>1. Enter Groq API key<br>2. Paste GitHub repo URL<br>3. Click Load Repository<br>4. Ask about the code</div>", unsafe_allow_html=True)

if load_btn:
    if not groq_key:
        st.error("Please enter your Groq API key.")
    elif not repo_url:
        st.error("Please enter a repository URL.")
    else:
        with st.spinner("Fetching and indexing repository..."):
            try:
                os.environ["GROQ_API_KEY"] = groq_key
                if github_token: os.environ["GITHUB_TOKEN"] = github_token
                docs = load_github_repo(repo_url, file_extensions, max_files, github_token or None)
                engine = RAGEngine(docs)
                st.session_state.rag_engine  = engine
                st.session_state.repo_loaded = True
                st.session_state.repo_url    = repo_url
                st.session_state.messages    = []
                st.success(f"Indexed {engine.num_files} files into {engine.num_chunks} chunks.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

st.markdown('<div class="page-header"><h1>RepoChat</h1><p>Ask questions about any GitHub repository</p></div>', unsafe_allow_html=True)

if not st.session_state.messages:
    if st.session_state.repo_loaded:
        st.markdown('<div class="empty-state"><h3>Repository indexed</h3><p>Type a question below to explore the codebase.</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state"><h3>No repository loaded</h3><p>Enter your Groq API key and a GitHub URL in the sidebar,<br>then click Load Repository.</p></div>', unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-bubble"><div class="bubble-label">You</div>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            sources_html = ""
            if msg.get("sources"):
                tags = "".join(f'<span class="source-tag">{s}</span>' for s in msg["sources"][:5])
                sources_html = f'<div style="margin-top:10px;border-top:1px solid #e8e4df;padding-top:8px"><div style="font-size:10px;font-weight:600;letter-spacing:0.8px;text-transform:uppercase;color:#888580;margin-bottom:5px">Sources</div>{tags}</div>'
            st.markdown(f'<div class="bot-bubble"><div class="bubble-label">Assistant</div>{msg["content"]}{sources_html}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input("Message", placeholder="Ask about the repository...", label_visibility="collapsed", disabled=not st.session_state.repo_loaded)
with col2:
    send_btn = st.button("Send", use_container_width=True, disabled=not st.session_state.repo_loaded)

if (send_btn or user_input) and user_input.strip():
    if not st.session_state.repo_loaded:
        st.warning("Please load a repository first.")
    elif not groq_key:
        st.warning("Please enter your Groq API key.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})
        with st.spinner("Thinking..."):
            try:
                os.environ["GROQ_API_KEY"] = groq_key
                answer, sources = st.session_state.rag_engine.query(user_input.strip())
                st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}", "sources": []})
        st.rerun()
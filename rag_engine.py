import re, math, os
from collections import Counter
from typing import List, Tuple
from groq import Groq

def chunk_document(doc, chunk_size=1200, overlap=150):
    text, path, source = doc["content"], doc["metadata"]["path"], doc["metadata"]["source"]
    lines, chunks, current, current_len = text.splitlines(keepends=True), [], [], 0
    for line in lines:
        current.append(line); current_len += len(line)
        if current_len >= chunk_size:
            chunk_text = "".join(current).strip()
            if chunk_text: chunks.append({"text": chunk_text, "source": source, "path": path})
            overlap_text = "".join(current)[-overlap:]
            current, current_len = [overlap_text], len(overlap_text)
    remainder = "".join(current).strip()
    if remainder: chunks.append({"text": remainder, "source": source, "path": path})
    # Always add a small header chunk with filename so file-level queries work
    header = f"File: {path}\n\n{text[:300]}"
    chunks.insert(0, {"text": header, "source": source, "path": path})
    return chunks

def tokenize(text):
    # include common programming keywords and short tokens
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    # also split on camelCase
    expanded = []
    for t in tokens:
        parts = re.sub(r'([A-Z])', r' \1', t).lower().split()
        expanded.extend(parts)
    return expanded

class TFIDFRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.doc_tokens = [tokenize(c["text"]) for c in chunks]
        N = len(self.doc_tokens); df = Counter()
        for tokens in self.doc_tokens: df.update(set(tokens))
        self.idf = {t: math.log((N+1)/(df[t]+1))+1 for t in df}
        self.tfidf_vecs = []
        for tokens in self.doc_tokens:
            tf = Counter(tokens); total = max(len(tokens),1)
            self.tfidf_vecs.append({t:(c/total)*self.idf.get(t,1) for t,c in tf.items()})

    def _cosine(self, a, b):
        keys = set(a)&set(b)
        if not keys: return 0.0
        dot=sum(a[k]*b[k] for k in keys)
        ma=math.sqrt(sum(v**2 for v in a.values())); mb=math.sqrt(sum(v**2 for v in b.values()))
        return dot/(ma*mb) if ma and mb else 0.0

    def retrieve(self, query, top_k=6):
        q=Counter(tokenize(query)); total=max(sum(q.values()),1)
        qv={t:(c/total)*self.idf.get(t,1) for t,c in q.items()}
        scores=[self._cosine(qv,v) for v in self.tfidf_vecs]
        # Return top_k regardless of score threshold so we always get results
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.chunks[i] for i in top]

class RAGEngine:
    def __init__(self, documents, chunk_size=1200):
        self.documents = documents
        all_chunks = []
        for doc in documents:
            all_chunks.extend(chunk_document(doc, chunk_size))
        self.chunks = all_chunks
        self.retriever = TFIDFRetriever(all_chunks)
        self.num_chunks = len(all_chunks)
        self.num_files = len(documents)
        # Build a repo summary for general questions
        self.repo_summary = self._build_summary()

    def _build_summary(self):
        lines = []
        for doc in self.documents:
            path = doc["metadata"]["path"]
            preview = doc["content"][:200].replace("\n", " ").strip()
            lines.append(f"- {path}: {preview}")
        return "\n".join(lines[:30])

    def query(self, question, top_k=6):
        relevant = self.retriever.retrieve(question, top_k)

        # Always build context — use relevant chunks + repo summary
        context_parts = []
        for c in relevant:
            context_parts.append(f"=== {c['path']} ===\n{c['text']}")
        context = "\n\n".join(context_parts)

        sources = list(dict.fromkeys(c["path"] for c in relevant))

        system_prompt = (
            "You are an expert code analyst. You have been given code files from a GitHub repository. "
            "Answer the user's question based on the code provided. "
            "Be specific — mention file names, function names, libraries imported, and languages used. "
            "If the question is general (like 'what language is used' or 'what does this project do'), "
            "summarize based on what you see in the files."
        )

        user_message = (
            f"Repository file list:\n{self.repo_summary}\n\n"
            f"Code context:\n\n{context}\n\n"
            f"Question: {question}"
        )

        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        return resp.choices[0].message.content, sources
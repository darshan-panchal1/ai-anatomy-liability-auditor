import { useState, useEffect, useRef, useCallback } from "react";

/* ─── Inject fonts + global styles once ─────────────────────────── */
const GLOBAL = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@300;400;500&family=DM+Serif+Display:ital@0;1&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0f12;--surface:#141720;--surface2:#1a1f2b;
  --border:#22283a;--border2:#2b3347;
  --accent:#4ade80;--accent-dim:rgba(74,222,128,.12);--accent-glow:rgba(74,222,128,.06);
  --text:#e2e8f0;--text-muted:#64748b;--text-dim:#3a4256;
  --red:#f87171;--red-dim:rgba(248,113,113,.1);
  --sans:'DM Sans',sans-serif;--mono:'DM Mono',monospace;--serif:'DM Serif Display',Georgia,serif;
  --r:8px;--r-lg:14px;
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:15px;line-height:1.65;min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");pointer-events:none;z-index:9999}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(74,222,128,.3)}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.report-md{font-size:15px;line-height:1.8;color:var(--text)}
.report-md h1,.report-md h2,.report-md h3,.report-md h4{font-family:var(--serif);font-weight:400;color:var(--text);margin:28px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.report-md h1{font-size:22px}.report-md h2{font-size:19px}
.report-md h3{font-size:16px;border-bottom:none;color:var(--accent)}
.report-md h4{font-size:14px;border-bottom:none;color:var(--text-muted)}
.report-md p{margin-bottom:14px}.report-md p:last-child{margin-bottom:0}
.report-md strong{color:var(--text);font-weight:600}.report-md em{color:var(--text-muted)}
.report-md ul,.report-md ol{padding-left:22px;margin-bottom:14px}
.report-md li{margin-bottom:6px}
.report-md code{font-family:var(--mono);font-size:13px;background:var(--surface2);color:var(--accent);padding:2px 6px;border-radius:4px}
.report-md pre{background:var(--surface2);border:1px solid var(--border);border-radius:var(--r);padding:16px 18px;margin-bottom:14px;overflow-x:auto}
.report-md pre code{background:none;padding:0;color:var(--text-muted)}
.report-md blockquote{border-left:3px solid rgba(74,222,128,.4);padding-left:16px;margin:16px 0;color:var(--text-muted);font-style:italic}
.report-md hr{border:none;border-top:1px solid var(--border);margin:24px 0}
.report-md table{width:100%;border-collapse:collapse;margin-bottom:14px;font-size:14px}
.report-md th{text-align:left;padding:8px 12px;border-bottom:1px solid var(--border2);font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted)}
.report-md td{padding:8px 12px;border-bottom:1px solid var(--border);vertical-align:top}
`;

if (!document.getElementById("ala-global")) {
  const s = document.createElement("style");
  s.id = "ala-global";
  s.textContent = GLOBAL;
  document.head.appendChild(s);
}

/* ─── Load marked.js from CDN ────────────────────────────────────── */
if (!document.getElementById("marked-script")) {
  const el = document.createElement("script");
  el.id = "marked-script";
  el.src = "https://cdn.jsdelivr.net/npm/marked/marked.min.js";
  document.head.appendChild(el);
}

function parseMarkdown(text) {
  return typeof window.marked !== "undefined"
    ? window.marked.parse(text)
    : text.replace(/\n/g, "<br/>");
}

/* ─── Data ───────────────────────────────────────────────────────── */
const RUNPOD_ENDPOINT_ID = import.meta.env.VITE_RUNPOD_ENDPOINT_ID;
const RUNPOD_API_KEY     = import.meta.env.VITE_RUNPOD_API_KEY;
const RUNPOD_URL         = `https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/runsync`;

const EXAMPLES = [
  "A patient developed brachial plexus injury following improper positioning during shoulder arthroscopy. No documentation of positioning precautions or risk disclosure was found. Determine liability exposure.",
  "During a laparoscopic cholecystectomy, the patient sustained a common bile duct injury due to misidentification of anatomy. The surgeon failed to follow the critical view of safety protocol and did not adequately disclose this risk preoperatively. Evaluate potential medical malpractice liability.",
  "Post spinal surgery, the patient experienced dural tear leading to CSF leak and neurological deficits. The complication was neither discussed in informed consent nor promptly managed. Assess negligence and standard-of-care deviation.",
  "A patient suffered a femoral nerve injury during a total hip replacement. The surgeon did not obtain informed consent for this known risk. Assess malpractice liability.",
];

const PIPELINE_NODES = [
  { id: "anatomy",  icon: "🧬", label: "Anatomy",  sub: "Wikidata SPARQL" },
  { id: "strategy", icon: "🔍", label: "Strategy", sub: "Query Generation" },
  { id: "legal",    icon: "⚖️", label: "Legal",    sub: "CourtListener" },
  { id: "auditor",  icon: "📋", label: "Auditor",  sub: "Synthesis" },
];

const STEPS = [
  { node: "anatomy",  msg: "Extracting anatomical entities via Wikidata SPARQL…",  delay: 0 },
  { node: "strategy", msg: "Formulating boolean legal search strategy…",            delay: 1200 },
  { node: "legal",    msg: "Querying CourtListener for precedents…",               delay: 2200 },
  { node: "auditor",  msg: "Synthesising liability report…",                        delay: 4000 },
];

/* ─── Pipeline node ─────────────────────────────────────────────── */
function PipeNode({ node, state }) {
  const s = state || "idle";
  const iconBg     = s === "active" ? "var(--accent-dim)" : s === "done" ? "rgba(74,222,128,.08)" : s === "error" ? "var(--red-dim)" : "var(--surface2)";
  const iconBorder = s === "active" ? "rgba(74,222,128,.4)" : s === "done" ? "rgba(74,222,128,.3)" : s === "error" ? "rgba(248,113,113,.4)" : "var(--border2)";
  const iconShadow = s === "active" ? "0 0 20px rgba(74,222,128,.15)" : "none";
  const labelColor = s === "active" || s === "done" ? "var(--accent)" : s === "error" ? "var(--red)" : "var(--text-muted)";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center",
                  minWidth: 110, padding: "14px 10px",
                  borderRadius: 10, border: "1px solid transparent", transition: "all .25s ease" }}>
      <div style={{ width: 44, height: 44, borderRadius: 10,
                    border: `1px solid ${iconBorder}`, background: iconBg,
                    boxShadow: iconShadow, display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: 18, marginBottom: 10, transition: "all .25s" }}>
        {node.icon}
      </div>
      <div style={{ fontSize: 12, fontWeight: 500, color: labelColor, textAlign: "center", transition: "color .25s" }}>
        {node.label}
      </div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-dim)", textAlign: "center", marginTop: 3 }}>
        {node.sub}
      </div>
    </div>
  );
}

function PipeArrow({ active }) {
  return (
    <div style={{ width: 32, height: 1, flexShrink: 0, position: "relative",
                  background: active ? "var(--accent)" : "var(--border2)", transition: "background .3s" }}>
      <div style={{ position: "absolute", right: -4, top: -3,
                    border: "4px solid transparent",
                    borderLeft: `6px solid ${active ? "var(--accent)" : "var(--border2)"}`,
                    transition: "border-left-color .3s" }} />
    </div>
  );
}

/* ─── App ────────────────────────────────────────────────────────── */
export default function App() {
  const [query,      setQuery]      = useState("");
  const [loading,    setLoading]    = useState(false);
  const [status,     setStatus]     = useState({ type: "idle", msg: "Ready — enter a case description and run the audit." });
  const [nodeStates, setNodeStates] = useState({});
  const [result,     setResult]     = useState(null);
  const [error,      setError]      = useState(null);
  const [groqOk,     setGroqOk]     = useState(null);
  const [courtOk,    setCourtOk]    = useState(null);

  const timersRef  = useRef([]);
  const resultsRef = useRef(null);

  /* ── Health check ── */
  const checkHealth = useCallback(async () => {
    try {
      const r = await fetch(`https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/health`, {
        headers: { "Authorization": `Bearer ${RUNPOD_API_KEY}` },
        signal: AbortSignal.timeout(3500),
      });
      if (r.ok) {
        const d = await r.json();
        const ready = d.workers?.ready >= 0;
        setGroqOk(ready);
        setCourtOk(ready);
      } else { setGroqOk(false); setCourtOk(false); }
    } catch { setGroqOk(false); setCourtOk(false); }
  }, []);

  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, 15000);
    return () => clearInterval(id);
  }, [checkHealth]);

  /* ── Audit ── */
  const runAudit = async () => {
    if (!query.trim() || query.trim().length < 10) {
      setStatus({ type: "err", msg: "Please enter a case description (minimum 10 characters)." });
      return;
    }
    setLoading(true);
    setResult(null);
    setError(null);
    setNodeStates({});
    setStatus({ type: "active", msg: "Initiating pipeline…" });
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    STEPS.forEach(({ node, msg, delay }) => {
      const id = setTimeout(() => {
        setNodeStates(prev => {
          const idx = PIPELINE_NODES.findIndex(n => n.id === node);
          return PIPELINE_NODES.reduce((acc, n, i) => ({
            ...acc,
            [n.id]: i < idx ? "done" : i === idx ? "active" : prev[n.id] || "idle",
          }), {});
        });
        setStatus({ type: "active", msg });
      }, delay);
      timersRef.current.push(id);
    });

    try {
      const res = await fetch(RUNPOD_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${RUNPOD_API_KEY}`,
        },
        body: JSON.stringify({ input: { query: query.trim() } }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(typeof err.detail === "object" ? JSON.stringify(err.detail) : err.detail);
      }
      const data = await res.json();
      if (data.status !== "COMPLETED") {
        throw new Error(`Job ${data.status}: ${data.error || "Unknown error"}`);
      }
      const output = data.output;
      const normalized = {
        ...output,
        duration_ms: data.executionTime,
        request_id:  data.id,
        metadata: {
          ...output.metadata,
          cases_cited: output.metadata.cases_found_count,
          legal_query: output.metadata.legal_query_used,
        },
      };
      setNodeStates(PIPELINE_NODES.reduce((a, n) => ({ ...a, [n.id]: "done" }), {}));
      setStatus({ type: "ok", msg: `Complete in ${normalized.duration_ms}ms · ${normalized.metadata.cases_cited} case(s) cited` });
      setResult(normalized);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    } catch (err) {
      setNodeStates(PIPELINE_NODES.reduce((a, n) => ({ ...a, [n.id]: "error" }), {}));
      setStatus({ type: "err", msg: `Error: ${err.message}` });
      setError(err.message);
    } finally {
      timersRef.current.forEach(clearTimeout);
      setLoading(false);
    }
  };

  /* ── Derived styles ── */
  const sDotColor = status.type === "active" || status.type === "ok" ? "var(--accent)" : status.type === "err" ? "var(--red)" : "var(--text-dim)";
  const svcDot = (ok) => ({
    width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
    background: ok === null ? "var(--text-dim)" : ok ? "var(--accent)" : "var(--red)",
    boxShadow: ok ? "0 0 8px rgba(74,222,128,.5)" : "none",
    transition: "background .3s",
  });

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)", fontFamily: "var(--sans)" }}>

      {/* ── Header ── */}
      <header style={{ padding: "18px 0", borderBottom: "1px solid var(--border)",
                       position: "sticky", top: 0, background: "rgba(13,15,18,.9)",
                       backdropFilter: "blur(20px)", zIndex: 100 }}>
        <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 24px",
                      display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8,
                          background: "var(--accent-dim)", border: "1px solid rgba(74,222,128,.25)",
                          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>⚖</div>
            <div>
              <div style={{ fontFamily: "var(--serif)", fontSize: 16, fontWeight: 400, letterSpacing: ".01em" }}>
                Anatomy-of-Liability
              </div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text-muted)",
                            letterSpacing: ".1em", textTransform: "uppercase" }}>
                Medical · Legal · AI
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {[["Groq", groqOk], ["CourtListener", courtOk]].map(([label, ok]) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 6,
                                        fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-muted)" }}>
                <div style={svcDot(ok)} />
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 24px" }}>

        {/* ── Hero ── */}
        <section style={{ padding: "72px 0 56px", textAlign: "center", position: "relative" }}>
          <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
                        background: "radial-gradient(ellipse 60% 50% at 50% 0%,rgba(74,222,128,.05) 0%,transparent 65%)" }} />
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 20,
                        fontFamily: "var(--mono)", fontSize: 11, letterSpacing: ".15em",
                        textTransform: "uppercase", color: "var(--accent)",
                        padding: "5px 14px", borderRadius: 20,
                        background: "var(--accent-dim)", border: "1px solid rgba(74,222,128,.2)" }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--accent)" }} />
            Agentic Medical Malpractice Analysis
          </div>
          <h1 style={{ fontFamily: "var(--serif)", fontSize: "clamp(36px,5.5vw,58px)",
                       fontWeight: 400, lineHeight: 1.1, letterSpacing: "-.01em", marginBottom: 18 }}>
            The <em style={{ fontStyle: "italic", color: "var(--accent)" }}>Anatomy</em> of<br />Liability Auditor
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: 15, fontWeight: 300,
                      maxWidth: 520, margin: "0 auto", lineHeight: 1.7 }}>
            Wikidata anatomical ontologies meet CourtListener case law through a 4-node
            LangGraph pipeline — structured liability assessments in seconds.
          </p>
        </section>

        {/* ── Pipeline ── */}
        <div style={{ marginBottom: 48, background: "var(--surface)",
                      border: "1px solid var(--border)", borderRadius: "var(--r-lg)", padding: 24 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center",
                        gap: 0, overflowX: "auto" }}>
            {PIPELINE_NODES.map((node, i) => (
              <div key={node.id} style={{ display: "flex", alignItems: "center" }}>
                <PipeNode node={node} state={nodeStates[node.id]} />
                {i < PIPELINE_NODES.length - 1 && (
                  <PipeArrow active={
                    nodeStates[node.id] === "done" ||
                    nodeStates[PIPELINE_NODES[i + 1]?.id] === "active"
                  } />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Form ── */}
        <div style={{ marginBottom: 32 }}>
          <label style={{ display: "block", fontFamily: "var(--mono)", fontSize: 11,
                          letterSpacing: ".1em", textTransform: "uppercase",
                          color: "var(--text-muted)", marginBottom: 10, fontWeight: 400 }}>
            Case Description
          </label>
          <div style={{ position: "relative", background: "var(--surface)",
                        border: "1px solid var(--border2)", borderRadius: "var(--r-lg)",
                        transition: "border-color .2s" }}>
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) runAudit(); }}
              placeholder="Describe the medical scenario — include the anatomical structure, procedure performed, and alleged breach of standard of care…"
              style={{ width: "100%", minHeight: 150, resize: "vertical",
                       background: "transparent", border: "none", outline: "none",
                       padding: "18px 20px", fontFamily: "var(--sans)", fontSize: 15,
                       color: "var(--text)", lineHeight: 1.65 }}
            />
            <div style={{ padding: "12px 16px 14px", borderTop: "1px solid var(--border)",
                          display: "flex", alignItems: "center", justifyContent: "space-between",
                          flexWrap: "wrap", gap: 10 }}>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {["Brachial Plexus Injury", "Bile Duct Injury", "Dural Tear Spinal Surgery", "Femoral Nerve Injury"]
                  .map((label, i) => (
                  <button key={i} onClick={() => setQuery(EXAMPLES[i])}
                    style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: ".03em",
                             border: "1px solid var(--border2)", background: "transparent",
                             color: "var(--text-dim)", padding: "4px 10px", borderRadius: 20,
                             cursor: "pointer", transition: "all .15s" }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor="rgba(74,222,128,.3)"; e.currentTarget.style.color="var(--accent)"; e.currentTarget.style.background="var(--accent-dim)"; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor="var(--border2)"; e.currentTarget.style.color="var(--text-dim)"; e.currentTarget.style.background="transparent"; }}
                  >{label}</button>
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 11,
                               color: query.length > 1800 ? "var(--red)" : "var(--text-dim)" }}>
                  {query.length} / 2000
                </span>
                <button onClick={runAudit} disabled={loading}
                  style={{ display: "flex", alignItems: "center", gap: 8,
                           background: "var(--accent)", color: "#0a0c10",
                           border: "none", borderRadius: "var(--r)", padding: "10px 22px",
                           fontFamily: "var(--sans)", fontSize: 14, fontWeight: 600,
                           cursor: loading ? "not-allowed" : "pointer",
                           transition: "all .2s", letterSpacing: ".01em",
                           whiteSpace: "nowrap", opacity: loading ? .45 : 1 }}
                  onMouseEnter={e => { if (!loading) { e.currentTarget.style.background="#6ee89a"; e.currentTarget.style.boxShadow="0 0 24px rgba(74,222,128,.3)"; e.currentTarget.style.transform="translateY(-1px)"; }}}
                  onMouseLeave={e => { e.currentTarget.style.background="var(--accent)"; e.currentTarget.style.boxShadow="none"; e.currentTarget.style.transform="none"; }}
                >
                  {loading && (
                    <div style={{ width: 14, height: 14,
                                  border: "2px solid rgba(10,12,16,.3)", borderTopColor: "#0a0c10",
                                  borderRadius: "50%", animation: "spin .65s linear infinite" }} />
                  )}
                  <span>{loading ? "Running" : "Run Audit"}</span>
                  {!loading && <span>→</span>}
                </button>
              </div>
            </div>
          </div>

          {/* Status row */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12,
                        fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-dim)", minHeight: 18 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                          background: sDotColor, transition: "background .3s",
                          animation: status.type === "active" ? "pulse .9s ease-in-out infinite" : "none" }} />
            <span style={{ color: status.type === "err" ? "var(--red)" : "var(--text-dim)" }}>
              {status.msg}
            </span>
          </div>
        </div>

        {/* ── Results ── */}
        {(result || error) && (
          <div ref={resultsRef} style={{ animation: "fadeUp .35s ease forwards" }}>
            {error ? (
              <div style={{ background: "var(--red-dim)", border: "1px solid rgba(248,113,113,.3)",
                            borderRadius: "var(--r-lg)", padding: "22px 26px", marginBottom: 16 }}>
                <div style={{ fontFamily: "var(--serif)", fontSize: 18, color: "var(--red)", marginBottom: 8 }}>
                  Audit Failed
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 12, lineHeight: 1.7,
                              color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>
                  {error}{"\n\nEnsure the RunPod endpoint is active and VITE_RUNPOD_ENDPOINT_ID / VITE_RUNPOD_API_KEY are set correctly."}
                </div>
              </div>
            ) : result && (
              <>
                {/* Header */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                              marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
                  <div style={{ fontFamily: "var(--serif)", fontSize: 22, fontWeight: 400 }}>
                    Liability Assessment
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {[
                      { label: `${result.metadata.cases_cited} case(s)`, green: true },
                      { label: `${result.duration_ms}ms`, green: false },
                      { label: `${result.request_id.slice(0, 8)}…`, green: false },
                    ].map(({ label, green }) => (
                      <span key={label} style={{ fontFamily: "var(--mono)", fontSize: 10,
                                                  letterSpacing: ".06em", padding: "4px 10px", borderRadius: 20,
                                                  background: green ? "var(--accent-dim)" : "var(--surface2)",
                                                  border: green ? "1px solid rgba(74,222,128,.2)" : "1px solid var(--border)",
                                                  color: green ? "var(--accent)" : "var(--text-muted)" }}>
                        {label}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Meta cards */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))",
                              gap: 12, marginBottom: 16 }}>
                  {[
                    { icon: "🔍", title: "Legal Search Query", body: result.metadata.legal_query || "—" },
                    { icon: "⚙", title: "Pipeline Metadata",
                      body: `request_id:  ${result.request_id}\nthread_id:   ${result.metadata.thread_id}\nduration:    ${result.duration_ms}ms\ncases_cited: ${result.metadata.cases_cited}\nanat_ctx:    ${result.metadata.anatomical_context_used}` },
                  ].map(({ icon, title, body }) => (
                    <div key={title} style={{ background: "var(--surface)", border: "1px solid var(--border)",
                                              borderRadius: "var(--r-lg)", overflow: "hidden" }}>
                      <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)",
                                    fontFamily: "var(--mono)", fontSize: 10, letterSpacing: ".1em",
                                    textTransform: "uppercase", color: "var(--text-muted)",
                                    background: "var(--surface2)", display: "flex", alignItems: "center", gap: 7 }}>
                        {icon} {title}
                      </div>
                      <div style={{ padding: "14px 16px", fontFamily: "var(--mono)", fontSize: 12,
                                    color: "var(--text)", lineHeight: 1.75, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                        {body}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Report */}
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)",
                              borderRadius: "var(--r-lg)", overflow: "hidden", marginBottom: 16 }}>
                  <div style={{ padding: "12px 20px", borderBottom: "1px solid var(--border)",
                                background: "var(--surface2)", display: "flex", alignItems: "center", gap: 8 }}>
                    <span>📋</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: ".12em",
                                   textTransform: "uppercase", color: "var(--text-muted)" }}>
                      Full Liability Analysis
                    </span>
                  </div>
                  <div className="report-md" style={{ padding: "28px 32px" }}
                    dangerouslySetInnerHTML={{ __html: parseMarkdown(result.report || "") }}
                  />
                </div>

                <p style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-dim)",
                            borderLeft: "2px solid var(--border2)", paddingLeft: 12,
                            marginTop: 4, lineHeight: 1.6 }}>
                  ⚠ AI-generated for educational and research purposes only. Not legal advice. Consult a licensed attorney for legal matters.
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "24px 0", marginTop: 80,
                       textAlign: "center", fontFamily: "var(--mono)", fontSize: 11,
                       color: "var(--text-dim)", letterSpacing: ".05em" }}>
        <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 24px" }}>
          Anatomy-of-Liability Auditor &nbsp;·&nbsp; LangGraph + Groq + RunPod &nbsp;·&nbsp;
          <a href="https://github.com/darshan-panchal1/ai-anatomy-liability-auditor" target="_blank" rel="noreferrer"
            style={{ color: "var(--text-dim)", textDecoration: "none" }}
            onMouseEnter={e => e.target.style.color = "var(--accent)"}
            onMouseLeave={e => e.target.style.color = "var(--text-dim)"}>GitHub ↗</a>
          &nbsp;·&nbsp; Educational &amp; Research Use Only
        </div>
      </footer>
    </div>
  );
}
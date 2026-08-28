"""Judge-facing console for the Autonomous Opportunity Operator."""

from html import escape


REFERENCE = {
    "source_url":
        "https://allthingsagentichackathon.devpost.com/rules",

    "source_event_id":
        "source-091e6bf0decc227abd845f848dc319501466196c857f3dddca73c1c844a6fb42",

    "text_sha256":
        "401079adb7c18cf5bfe1c70a081e82628dd81b9c950ac8ecaab7a3d32c355285",

    "text_length":
        47306,

    "decision_event_id":
        "decision-64bcc823e7647256fc4d9fe81080aa04bca46b353df47d3599d45e528feb1549",

    "runtime_seconds":
        94.331408352,

    "disposition":
        "DECISION_REQUIRED",

    "reason_codes": [
        "REGISTRATION_APPROVAL_REQUIRED",
        "CLOUD_RESOURCE_CREATION_APPROVAL_REQUIRED",
        "EXTERNAL_SUBMISSION_APPROVAL_REQUIRED",
    ],

    "agents": [
        "Discovery",
        "Primary Source Verification",
        "Deterministic Hard Gate",
        "Investigation",
        "Failure Memory",
        "Economic Evidence",
        "Final Adjudication",
    ],

    "tools": [
        "Eligibility · Capital · Deadline Gate",
        "Failure Memory Similarity Check",
        "Unit Economics",
        "Final Evidence & Safety Adjudication",
    ],

    "stages": [
        "PRIMARY SOURCE VERIFICATION",
        "DETERMINISTIC HARD GATE",
        "INVESTIGATION",
        "FAILURE MEMORY",
        "ECONOMIC EVIDENCE",
        "FINAL ADJUDICATION",
    ],
}


def render_judge_console():
    """Return dependency-free judge-console HTML."""

    source_url = escape(
        REFERENCE["source_url"]
    )

    agents = "\n".join(
        f"""
        <div class="agent">
          <div class="agent-dot"></div>
          <div>
            <div class="agent-name">{escape(name)}</div>
            <div class="agent-status">verified execution</div>
          </div>
        </div>
        """
        for name in REFERENCE["agents"]
    )

    stages = "\n".join(
        f"""
        <div class="stage">
          <div class="stage-index">{index}</div>
          <div class="stage-copy">
            <strong>{escape(stage)}</strong>
            <span>ADK evidence observed</span>
          </div>
          <div class="stage-check">✓</div>
        </div>
        """
        for index, stage in enumerate(
            REFERENCE["stages"],
            start=1,
        )
    )

    tools = "\n".join(
        f"""
        <div class="tool">
          <span class="tool-lock">◆</span>
          <span>{escape(name)}</span>
          <b>authoritative</b>
        </div>
        """
        for name in REFERENCE["tools"]
    )

    human_reason_labels = {
        "REGISTRATION_APPROVAL_REQUIRED":
            "Registration requires your approval",

        "CLOUD_RESOURCE_CREATION_APPROVAL_REQUIRED":
            "Cloud resource creation requires your approval",

        "EXTERNAL_SUBMISSION_APPROVAL_REQUIRED":
            "External submission requires your approval",
    }

    reasons = "\n".join(
        (
            "<li>"
            "<span>"
            + escape(
                human_reason_labels.get(
                    reason,
                    reason,
                )
            )
            + "</span>"
            '<small class="machine-code">'
            + escape(reason)
            + "</small>"
            "</li>"
        )
        for reason in REFERENCE["reason_codes"]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Autonomous Opportunity Operator</title>

<style>
:root {{
  color-scheme: dark;
  --bg: #07090f;
  --panel: rgba(16, 20, 31, .78);
  --panel-2: rgba(20, 25, 40, .72);
  --line: rgba(255,255,255,.10);
  --muted: #929bb0;
  --text: #f6f8ff;
  --blue: #83a7ff;
  --violet: #b49cff;
  --green: #6ee7b7;
  --amber: #ffd27d;
  --red: #ff8f9c;
  --shadow: 0 28px 90px rgba(0,0,0,.38);
}}

* {{
  box-sizing: border-box;
}}

html {{
  scroll-behavior: smooth;
}}

body {{
  margin: 0;
  min-height: 100vh;
  background:
    radial-gradient(
      circle at 15% -5%,
      rgba(77, 113, 255, .22),
      transparent 34%
    ),
    radial-gradient(
      circle at 88% 12%,
      rgba(172, 116, 255, .15),
      transparent 28%
    ),
    linear-gradient(
      180deg,
      #07090f 0%,
      #0a0d14 55%,
      #07090f 100%
    );
  color: var(--text);
  font-family:
    Inter,
    ui-sans-serif,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}}

button,
input,
textarea {{
  font: inherit;
}}

.shell {{
  width: min(1480px, calc(100% - 40px));
  margin: 0 auto;
  padding: 30px 0 70px;
}}

.topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 44px;
}}

.brand {{
  display: flex;
  align-items: center;
  gap: 13px;
  font-weight: 760;
  letter-spacing: -.02em;
}}

.brand-mark {{
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 12px;
  background:
    linear-gradient(
      135deg,
      rgba(131,167,255,.25),
      rgba(180,156,255,.13)
    );
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.12);
}}

.system-state {{
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 13px;
  background: rgba(10,13,20,.72);
}}

.live-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 14px rgba(110,231,183,.72);
}}

.hero {{
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(390px, .75fr);
  gap: 22px;
  align-items: stretch;
  margin-bottom: 22px;
}}

.hero-copy {{
  padding: 46px 46px 40px;
  border: 1px solid var(--line);
  border-radius: 28px;
  background:
    linear-gradient(
      145deg,
      rgba(20,25,40,.88),
      rgba(13,16,26,.70)
    );
  box-shadow: var(--shadow);
}}

.eyebrow {{
  display: inline-flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 24px;
  color: #c9d5ff;
  text-transform: uppercase;
  letter-spacing: .13em;
  font-size: 11px;
  font-weight: 800;
}}

.hero h1 {{
  max-width: 820px;
  margin: 0;
  font-size: clamp(45px, 5vw, 78px);
  line-height: .96;
  letter-spacing: -.065em;
  font-weight: 780;
}}

.hero h1 span {{
  background:
    linear-gradient(
      90deg,
      #91b0ff,
      #d4b6ff
    );
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}}

.hero-lead {{
  max-width: 760px;
  margin: 26px 0 0;
  color: #b4bdd0;
  font-size: 18px;
  line-height: 1.65;
}}

.hero-proof {{
  padding: 28px;
  border: 1px solid var(--line);
  border-radius: 28px;
  background: var(--panel);
  box-shadow: var(--shadow);
}}

.mode-label {{
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 24px;
}}

.mode-chip {{
  padding: 8px 11px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
  border: 1px solid rgba(110,231,183,.22);
  color: var(--green);
  background: rgba(110,231,183,.07);
}}

.reference-note {{
  color: var(--muted);
  font-size: 12px;
  text-align: right;
}}

.benefit-line {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 22px;
  padding: 9px 12px;
  border: 1px solid rgba(131,167,255,.16);
  border-radius: 999px;
  color: #c7d4f2;
  background: rgba(131,167,255,.055);
  font-size: 12px;
}}

.benefit-line strong {{
  color: #f4f7ff;
}}

.decision-hero-label {{
  margin-top: 14px;
  color: var(--amber);
  text-transform: uppercase;
  letter-spacing: .12em;
  font-size: 10px;
  font-weight: 820;
}}

.decision-hero-value {{
  margin-top: 9px;
  font-size: clamp(38px, 4vw, 58px);
  line-height: .93;
  letter-spacing: -.055em;
  font-weight: 790;
}}

.proof-number {{
  font-size: 66px;
  line-height: 1;
  font-weight: 760;
  letter-spacing: -.06em;
}}

.proof-number span {{
  margin-left: 5px;
  color: var(--muted);
  font-size: 18px;
  letter-spacing: -.02em;
}}

.proof-caption {{
  margin-top: 9px;
  color: var(--muted);
}}

.proof-delta {{
  margin-top: 22px;
  padding: 16px;
  border: 1px solid rgba(110,231,183,.15);
  border-radius: 16px;
  color: #ccefe1;
  background: rgba(110,231,183,.055);
  line-height: 1.5;
}}

.metrics {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin: 18px 0 22px;
}}

.metric {{
  padding: 20px 21px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
}}

.metric strong {{
  display: block;
  font-size: 27px;
  letter-spacing: -.04em;
}}

.metric span {{
  display: block;
  margin-top: 5px;
  color: var(--muted);
  font-size: 12px;
}}

.grid {{
  display: grid;
  grid-template-columns: 1.08fr .92fr;
  gap: 22px;
  margin-top: 22px;
}}

.panel {{
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--panel);
  box-shadow: var(--shadow);
  overflow: hidden;
}}

.panel-head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 26px 20px;
  border-bottom: 1px solid var(--line);
}}

.panel-title {{
  font-size: 16px;
  font-weight: 740;
}}

.panel-subtitle {{
  margin-top: 5px;
  color: var(--muted);
  font-size: 12px;
}}

.panel-body {{
  padding: 24px 26px 27px;
}}

.agents {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 11px;
}}

.agent {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255,255,255,.025);
}}

.agent:last-child {{
  grid-column: span 2;
}}

.agent-dot {{
  width: 9px;
  height: 9px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--blue);
  box-shadow: 0 0 12px rgba(131,167,255,.55);
}}

.agent-name {{
  font-size: 13px;
  font-weight: 680;
}}

.agent-status {{
  margin-top: 3px;
  color: var(--muted);
  font-size: 10px;
}}

.stage {{
  display: grid;
  grid-template-columns: 32px 1fr 26px;
  gap: 13px;
  align-items: center;
  padding: 13px 0;
}}

.stage + .stage {{
  border-top: 1px solid rgba(255,255,255,.075);
}}

.stage-index {{
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: rgba(131,167,255,.10);
  color: #bed0ff;
  font-size: 11px;
  font-weight: 780;
}}

.stage-copy strong {{
  display: block;
  font-size: 12px;
  letter-spacing: .03em;
}}

.stage-copy span {{
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 10px;
}}

.stage-check {{
  color: var(--green);
  font-weight: 800;
}}

.tools {{
  display: grid;
  gap: 10px;
}}

.tool {{
  display: grid;
  grid-template-columns: 24px 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 12px 13px;
  border-radius: 13px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.024);
  font-size: 12px;
}}

.tool-lock {{
  color: var(--amber);
}}

.tool b {{
  color: var(--amber);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: .08em;
}}

.decision {{
  margin-top: 17px;
  padding: 18px;
  border: 1px solid rgba(255,210,125,.22);
  border-radius: 17px;
  background: rgba(255,210,125,.055);
}}

.decision-label {{
  color: var(--amber);
  text-transform: uppercase;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .1em;
}}

.decision-value {{
  margin: 7px 0 12px;
  font-size: 25px;
  font-weight: 760;
  letter-spacing: -.035em;
}}

.decision ul {{
  margin: 0;
  padding: 0;
  list-style: none;
  color: #ddd6c1;
  font-size: 12px;
}}

.decision li {{
  padding: 9px 0;
}}

.decision li + li {{
  border-top: 1px solid rgba(255,210,125,.10);
}}

.decision li span {{
  display: block;
  font-weight: 650;
}}

.machine-code {{
  display: block;
  margin-top: 3px;
  color: #8d897f;
  font-family:
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Consolas,
    monospace;
  font-size: 8px;
  letter-spacing: .02em;
}}

.source-card {{
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255,255,255,.022);
}}

.label {{
  color: var(--muted);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .09em;
  font-weight: 800;
}}

.source-url {{
  margin: 8px 0 13px;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.45;
}}

.hash {{
  font-family:
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Consolas,
    monospace;
  color: #9ba7c3;
  font-size: 10px;
  word-break: break-all;
}}

.proof-strip {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 14px;
}}

.proof-cell {{
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 13px;
}}

.proof-cell strong {{
  display: block;
  font-size: 15px;
}}

.proof-cell span {{
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 9px;
}}

.live-panel {{
  margin-top: 22px;
  border:
    1px solid rgba(131,167,255,.20);
  border-radius: 26px;
  background:
    linear-gradient(
      145deg,
      rgba(18,24,39,.93),
      rgba(11,14,23,.88)
    );
  box-shadow: var(--shadow);
}}

.live-layout {{
  display: grid;
  grid-template-columns: .9fr 1.1fr;
}}

.live-form {{
  padding: 29px;
  border-right: 1px solid var(--line);
}}

.live-output {{
  min-height: 520px;
  padding: 29px;
}}

.live-badge {{
  display: inline-block;
  margin-bottom: 18px;
  padding: 7px 9px;
  border: 1px solid rgba(131,167,255,.2);
  border-radius: 999px;
  color: #b9ccff;
  background: rgba(131,167,255,.07);
  text-transform: uppercase;
  font-size: 9px;
  letter-spacing: .11em;
  font-weight: 800;
}}

.live-form h2 {{
  margin: 0 0 8px;
  font-size: 27px;
  letter-spacing: -.035em;
}}

.live-form p {{
  margin: 0 0 22px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.55;
}}

.field {{
  margin-top: 14px;
}}

.field label {{
  display: block;
  margin-bottom: 7px;
  color: #b1bacd;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .08em;
  font-weight: 750;
}}

.field input,
.field textarea {{
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  outline: none;
  padding: 12px 13px;
  color: var(--text);
  background: rgba(5,7,12,.65);
}}

.field textarea {{
  min-height: 102px;
  resize: vertical;
}}

.field input:focus,
.field textarea:focus {{
  border-color: rgba(131,167,255,.55);
  box-shadow: 0 0 0 3px rgba(131,167,255,.08);
}}

.two-fields {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 11px;
}}

.actions {{
  display: flex;
  gap: 10px;
  margin-top: 19px;
}}

.button {{
  cursor: pointer;
  border: 0;
  border-radius: 12px;
  padding: 12px 15px;
  font-weight: 720;
}}

.button-primary {{
  color: #07101f;
  background:
    linear-gradient(
      90deg,
      #91b0ff,
      #c1adff
    );
}}

.button-secondary {{
  color: #d9e0ef;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.04);
}}

.button:disabled {{
  cursor: not-allowed;
  opacity: .45;
}}

.output-placeholder {{
  height: 100%;
  min-height: 360px;
  display: grid;
  place-items: center;
  text-align: center;
  color: var(--muted);
}}

.output-placeholder strong {{
  display: block;
  margin-bottom: 8px;
  color: #c7d1e7;
  font-size: 16px;
}}

.placeholder-wrap {{
  width: min(100%, 560px);
  text-align: left;
}}

.placeholder-intro {{
  margin-bottom: 18px;
  text-align: center;
}}

.placeholder-steps {{
  display: grid;
  gap: 10px;
}}

.placeholder-step {{
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 12px;
  align-items: center;
  padding: 12px 13px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: rgba(255,255,255,.022);
}}

.placeholder-step b {{
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  color: #bed0ff;
  background: rgba(131,167,255,.10);
  font-size: 10px;
}}

.placeholder-step strong {{
  margin: 0 0 3px;
  font-size: 12px;
}}

.placeholder-step span {{
  color: var(--muted);
  font-size: 10px;
  line-height: 1.45;
}}

.live-result {{
  display: none;
}}

.live-result.visible {{
  display: block;
}}

.result-top {{
  display: flex;
  justify-content: space-between;
  gap: 15px;
  align-items: start;
  margin-bottom: 20px;
}}

.result-disposition {{
  font-size: 27px;
  font-weight: 780;
  letter-spacing: -.04em;
}}

.result-runtime {{
  text-align: right;
  color: var(--muted);
  font-size: 11px;
}}

.result-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}}

.result-card {{
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: rgba(255,255,255,.022);
}}

.result-card strong {{
  display: block;
  font-size: 16px;
}}

.result-card span {{
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: .07em;
}}

.reason-list {{
  margin-top: 16px;
  padding: 15px;
  border: 1px solid var(--line);
  border-radius: 14px;
  color: #b7c0d3;
  font-size: 11px;
  line-height: 1.7;
}}

.footer {{
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: 28px;
  padding: 20px 4px 0;
  color: #70798d;
  font-size: 10px;
}}

@media (max-width: 1000px) {{
  .hero,
  .grid,
  .live-layout {{
    grid-template-columns: 1fr;
  }}

  .live-form {{
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }}

  .metrics {{
    grid-template-columns: repeat(2, 1fr);
  }}
}}

@media (max-width: 650px) {{
  .shell {{
    width: min(100% - 22px, 1480px);
    padding-top: 18px;
  }}

  .hero-copy {{
    padding: 30px 24px;
  }}

  .hero h1 {{
    font-size: 45px;
  }}

  .metrics,
  .agents,
  .proof-strip,
  .result-grid,
  .two-fields {{
    grid-template-columns: 1fr;
  }}

  .agent:last-child {{
    grid-column: auto;
  }}

  .topbar,
  .footer {{
    align-items: flex-start;
    flex-direction: column;
  }}
}}
</style>
</head>

<body>
<div class="shell">

  <header class="topbar">
    <div class="brand">
      <div class="brand-mark">A</div>
      <div>Autonomous Opportunity Operator</div>
    </div>

    <div class="system-state">
      <span class="live-dot"></span>
      <span id="cloudState">Google Cloud provenance loading…</span>
    </div>
  </header>

  <section class="hero">

    <div class="hero-copy">
      <div class="eyebrow">
        Google ADK · Gemini · Deterministic Authority
      </div>

      <h1>
        From messy opportunity to
        <span>evidence-backed decision.</span>
      </h1>

      <p class="hero-lead">
        A seven-agent Google ADK team reads the source, verifies the
        facts, checks constraints, remembers prior failures, tests the
        economics, and stops before consequential external action
        without human approval.
      </p>

      <div class="benefit-line">
        <strong>Not a chatbot.</strong>
        It completes an auditable workflow; you keep authority.
      </div>
    </div>

    <div class="hero-proof">
      <div class="mode-label">
        <div class="mode-chip">Verified Reference Run</div>
        <div class="reference-note">
          Real cloud execution · Aug 14
        </div>
      </div>

      <div class="decision-hero-label">
        FINAL OUTCOME
      </div>

      <div class="decision-hero-value">
        DECISION<br>REQUIRED
      </div>

      <div class="proof-caption">
        Human approval is required before registration,
        cloud resource creation or external submission.
      </div>

      <div class="proof-delta">
        The system completed the real seven-agent workflow in
        <strong>94.3s</strong> after previously hitting a
        <strong>300s timeout</strong>—then stopped exactly where
        human authority begins.
      </div>
    </div>

  </section>

  <section class="metrics">
    <div class="metric">
      <strong>47,306</strong>
      <span>source characters verified</span>
    </div>

    <div class="metric">
      <strong>7</strong>
      <span>specialist agents completed the job</span>
    </div>

    <div class="metric">
      <strong>4</strong>
      <span>deterministic checks remained authoritative</span>
    </div>

    <div class="metric">
      <strong>0</strong>
      <span>consequential actions without approval</span>
    </div>
  </section>

  <section class="grid">

    <article class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Autonomous agent team</div>
          <div class="panel-subtitle">
            Seven specialists hand off evidence, not chat
          </div>
        </div>
        <div class="mode-chip">7 agents</div>
      </div>

      <div class="panel-body">
        <div class="agents">
          {agents}
        </div>
      </div>
    </article>

    <article class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Workflow trace</div>
          <div class="panel-subtitle">
            Every stage completed and remained auditable
          </div>
        </div>
      </div>

      <div class="panel-body">
        {stages}
      </div>
    </article>

    <article class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Deterministic authority layer</div>
          <div class="panel-subtitle">
            The model cannot overrule these results
          </div>
        </div>
      </div>

      <div class="panel-body">

        <div class="tools">
          {tools}
        </div>

        <div class="decision">
          <div class="decision-label">
            Human authority boundary
          </div>

          <div class="decision-value">
            DECISION REQUIRED
          </div>

          <div class="machine-code">
            DECISION_REQUIRED
          </div>

          <ul>
            {reasons}
          </ul>
        </div>

      </div>
    </article>

    <article class="panel">

      <div class="panel-head">
        <div>
          <div class="panel-title">Proof, not claims</div>
          <div class="panel-subtitle">
            Primary-source and durable-runtime evidence
          </div>
        </div>
      </div>

      <div class="panel-body">

        <div class="source-card">
          <div class="label">Primary source</div>
          <div class="source-url">{source_url}</div>

          <div class="label">Evidence fingerprint · SHA-256</div>
          <div class="hash">
            {REFERENCE["text_sha256"]}
          </div>
        </div>

        <div class="proof-strip">
          <div class="proof-cell">
            <strong>{REFERENCE["text_length"]:,}</strong>
            <span>verified text characters</span>
          </div>

          <div class="proof-cell">
            <strong>17</strong>
            <span>normalized ADK events</span>
          </div>

          <div class="proof-cell">
            <strong>&lt;1s</strong>
            <span>durable replay</span>
          </div>
        </div>

        <div class="source-card" style="margin-top:14px">
          <div class="label">Replay guarantee</div>
          <div style="margin-top:8px;font-size:13px">
            Same source + same decision profile →
            <strong>0 additional ADK workflows</strong>.
          </div>
        </div>

      </div>
    </article>

  </section>

  <section class="live-panel">

    <div class="live-layout">

      <div class="live-form">
        <div class="live-badge">Live Analysis</div>

        <h2>Give the team a real opportunity.</h2>

        <p>
          Nothing runs automatically. Preflight checks only the source.
          The seven-agent Gemini workflow starts only when you explicitly
          press the live-analysis button.
        </p>

        <div class="field">
          <label for="sourceUrl">Primary-source URL</label>
          <input
            id="sourceUrl"
            value="{source_url}"
            autocomplete="off"
          >
        </div>

        <div class="two-fields">

          <div class="field">
            <label for="jurisdiction">Jurisdiction</label>
            <input id="jurisdiction" value="Bulgaria">
          </div>

          <div class="field">
            <label for="capital">Available capital</label>
            <input id="capital" value="150">
          </div>

        </div>

        <div class="two-fields">

          <div class="field">
            <label for="cashSpend">Max cash spend</label>
            <input id="cashSpend" value="0">
          </div>

          <div class="field">
            <label for="humanHours">Max human hours</label>
            <input id="humanHours" value="8">
          </div>

        </div>

        <div class="field">
          <label for="objective">Objective</label>
          <textarea id="objective">Determine whether pursuing this opportunity merits further human attention under the supplied constraints; do not register, submit, spend money, represent the operator, or take consequential external action.</textarea>
        </div>

        <div class="actions">
          <button
            class="button button-secondary"
            id="preflightButton"
            type="button"
          >
            Preflight source
          </button>

          <button
            class="button button-primary"
            id="liveButton"
            type="button"
          >
            Run live 7-agent analysis
          </button>
        </div>
      </div>

      <div class="live-output">

        <div
          class="output-placeholder"
          id="outputPlaceholder"
        >
          <div class="placeholder-wrap">

            <div class="placeholder-intro">
              <strong>What the team will do</strong>
              Source preflight is model-free. The Google ADK workflow
              starts only after your explicit click.
            </div>

            <div class="placeholder-steps">

              <div class="placeholder-step">
                <b>01</b>
                <div>
                  <strong>Read &amp; verify</strong>
                  <span>
                    Capture the primary source, verify facts and
                    preserve provenance.
                  </span>
                </div>
              </div>

              <div class="placeholder-step">
                <b>02</b>
                <div>
                  <strong>Test &amp; remember</strong>
                  <span>
                    Apply deterministic gates, investigate execution,
                    check failure memory and economics.
                  </span>
                </div>
              </div>

              <div class="placeholder-step">
                <b>03</b>
                <div>
                  <strong>Decide &amp; stop safely</strong>
                  <span>
                    Produce an evidence-backed disposition and stop
                    before any action requiring human authority.
                  </span>
                </div>
              </div>

            </div>
          </div>
        </div>

        <div
          class="live-result"
          id="liveResult"
        >
          <div class="result-top">
            <div>
              <div class="label">Final disposition</div>
              <div
                class="result-disposition"
                id="resultDisposition"
              >
                —
              </div>
            </div>

            <div
              class="result-runtime"
              id="resultRuntime"
            ></div>
          </div>

          <div class="result-grid">
            <div class="result-card">
              <strong id="resultAgents">—</strong>
              <span>agents observed</span>
            </div>

            <div class="result-card">
              <strong id="resultTools">—</strong>
              <span>tools called</span>
            </div>

            <div class="result-card">
              <strong id="resultStages">—</strong>
              <span>coordinator stages</span>
            </div>

            <div class="result-card">
              <strong id="resultReplay">—</strong>
              <span>replayed</span>
            </div>
          </div>

          <div
            class="reason-list"
            id="resultReasons"
          ></div>

          <div
            class="source-card"
            style="margin-top:16px"
          >
            <div class="label">Evidence</div>
            <div
              class="hash"
              id="resultEvidence"
              style="margin-top:8px"
            ></div>
          </div>
        </div>

      </div>

    </div>

  </section>

  <footer class="footer">
    <span>
      Autonomous Opportunity Operator · Google ADK + Gemini
    </span>

    <span>
      Human approval remains mandatory for consequential external action.
    </span>
  </footer>

</div>

<script>
(() => {{
  "use strict";

  const q = (id) => document.getElementById(id);

  const sourceUrl = q("sourceUrl");
  const jurisdiction = q("jurisdiction");
  const capital = q("capital");
  const cashSpend = q("cashSpend");
  const humanHours = q("humanHours");
  const objective = q("objective");

  const preflightButton = q("preflightButton");
  const liveButton = q("liveButton");

  const placeholder = q("outputPlaceholder");
  const result = q("liveResult");

  let counter = 0;

  function newOpportunityId(prefix) {{
    counter += 1;

    return (
      prefix
      + "-"
      + Date.now().toString(36)
      + "-"
      + counter.toString(36)
    );
  }}

  function busy(button, yes, busyText, idleText) {{
    button.disabled = yes;
    button.textContent = yes ? busyText : idleText;
  }}

  function showText(title, detail) {{
    placeholder.style.display = "grid";
    result.classList.remove("visible");

    placeholder.replaceChildren();

    const wrap = document.createElement("div");
    const strong = document.createElement("strong");

    strong.textContent = title;

    const body = document.createElement("div");
    body.textContent = detail;

    wrap.appendChild(strong);
    wrap.appendChild(body);
    placeholder.appendChild(wrap);
  }}

  function showDecision(data, elapsed) {{
    placeholder.style.display = "none";
    result.classList.add("visible");

    const outcome = data.outcome || {{}};
    const runtime = data.runtime_evidence || {{}};
    const source = data.source_evidence || {{}};

    q("resultDisposition").textContent =
      outcome.disposition || data.status || "UNKNOWN";

    q("resultRuntime").textContent =
      elapsed.toFixed(1) + "s · "
      + (runtime.workflow_state || "runtime unavailable");

    q("resultAgents").textContent =
      String((runtime.agents_seen || []).length) + " / 7";

    q("resultTools").textContent =
      String((runtime.tools_called || []).length) + " / 4";

    q("resultStages").textContent =
      String((outcome.stage_trace || []).length) + " / 6";

    q("resultReplay").textContent =
      outcome.replayed === true ? "YES" : "NO";

    const reasons = outcome.reason_codes || data.reason_codes || [];

    q("resultReasons").textContent =
      reasons.length
        ? reasons.join(" · ")
        : "No reason codes returned.";

    q("resultEvidence").textContent =
      "decision="
      + (data.decision_event_id || "n/a")
      + " · source="
      + (source.source_event_id || "n/a")
      + " · text_sha256="
      + (source.text_sha256 || "n/a");
  }}

  async function jsonFetch(url, options) {{
    const response = await fetch(url, options);

    let data;

    try {{
      data = await response.json();
    }} catch (_) {{
      throw new Error(
        "Non-JSON response · HTTP " + response.status
      );
    }}

    if (!response.ok) {{
      throw new Error(
        "HTTP "
        + response.status
        + " · "
        + JSON.stringify(data)
      );
    }}

    return data;
  }}

  preflightButton.addEventListener(
    "click",
    async () => {{

      busy(
        preflightButton,
        true,
        "Checking source…",
        "Preflight source"
      );

      showText(
        "Primary-source preflight",
        "Capturing and validating source provenance. No model workflow is being run."
      );

      try {{
        const data = await jsonFetch(
          "/intake/primary-source",
          {{
            method: "POST",
            headers: {{
              "Content-Type": "application/json"
            }},
            body: JSON.stringify({{
              source_url: sourceUrl.value.trim(),
              opportunity_id:
                newOpportunityId("judge-preflight")
            }})
          }}
        );

        showText(
          data.status === "PASS"
            ? "Source verified"
            : "Source rejected",
          data.status === "PASS"
            ? (
                String(data.text_length)
                + " normalized characters · "
                + String(data.text_sha256)
              )
            : (
                (data.reason_codes || []).join(" · ")
                || "Fail closed"
              )
        );

      }} catch (error) {{
        showText(
          "Preflight error",
          String(error.message || error)
        );

      }} finally {{
        busy(
          preflightButton,
          false,
          "Checking source…",
          "Preflight source"
        );
      }}
    }}
  );

  liveButton.addEventListener(
    "click",
    async () => {{

      busy(
        liveButton,
        true,
        "Seven-agent team working…",
        "Run live 7-agent analysis"
      );

      showText(
        "Seven-agent team working",
        "Discovery → verification → deterministic gate → investigation → failure memory → economics → final adjudication."
      );

      const started = performance.now();

      try {{
        const data = await jsonFetch(
          "/decision/primary-source",
          {{
            method: "POST",
            headers: {{
              "Content-Type": "application/json"
            }},
            body: JSON.stringify({{
              source_url: sourceUrl.value.trim(),

              opportunity_id:
                newOpportunityId("judge-live"),

              decision_profile: {{
                operator_jurisdiction:
                  jurisdiction.value.trim(),

                available_capital:
                  capital.value.trim(),

                max_cash_spend:
                  cashSpend.value.trim(),

                max_human_hours:
                  humanHours.value.trim(),

                objective:
                  objective.value.trim()
              }}
            }})
          }}
        );

        const elapsed =
          (performance.now() - started) / 1000;

        showDecision(data, elapsed);

      }} catch (error) {{
        showText(
          "Live analysis stopped",
          String(error.message || error)
        );

      }} finally {{
        busy(
          liveButton,
          false,
          "Seven-agent team working…",
          "Run live 7-agent analysis"
        );
      }}
    }}
  );

  async function loadProvenance() {{
    try {{
      const data = await jsonFetch(
        "/provenance",
        {{
          method: "GET"
        }}
      );

      const revision =
        data.revision || "local";

      const model =
        data.model_id || "Gemini";

      q("cloudState").textContent =
        revision + " · " + model;

    }} catch (_) {{
      q("cloudState").textContent =
        "local console";
    }}
  }}

  loadProvenance();
}})();
</script>

</body>
</html>
"""


__all__ = [
    "REFERENCE",
    "render_judge_console",
]

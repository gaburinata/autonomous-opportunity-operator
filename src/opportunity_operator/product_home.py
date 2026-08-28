from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any

if __package__:
    from .product_integration import adapt_explicit_feed_item, build_product_view
else:
    # Some legacy proof tests load this file directly while keeping ``src``
    # on sys.path. Preserve that supported import mode without masking errors
    # raised from inside product_integration.
    from opportunity_operator.product_integration import adapt_explicit_feed_item, build_product_view


_REASON_LABELS = {
    "APPLICANT_LOCATION_NOT_CONFIRMED":
        "Applicant location not confirmed",

    "APPLICANT_JURISDICTION_NOT_CONFIRMED":
        "Applicant jurisdiction not confirmed",

    "DIRECT_ACTIVE_PROJECT_CONFLICT":
        "Conflicts with an active project",

    "ACTIVE_PROJECT_CAPACITY_CONFLICT":
        "Current project capacity is constrained",

    "T_MINUS_14_ALREADY_PASSED":
        "Preferred preparation window has already passed",

    "CHALLENGE_DATA_ACCESS_UNCONFIRMED":
        "Required challenge data access is not confirmed",

    "OFFICIAL_DEADLINE_TIME_CONFLICT":
        "Official deadline time needs verification",

    "DETAILED_ELIGIBILITY_NOT_VERIFIED":
        "Detailed eligibility still needs verification",

    "AWARD_SIZE_AND_RATE_NOT_VERIFIED":
        "Award size and funding rate need verification",

    "LIKELY_CONSORTIUM_SCALE":
        "Likely requires consortium-scale participation",
}


def _text(
    value: Any,
    fallback: str = "Not confirmed",
) -> str:
    if value is None:
        return fallback

    value = str(value).strip()
    return value or fallback


def _reason(value: Any) -> str:
    raw = str(value)

    return _REASON_LABELS.get(
        raw,
        raw.replace("_", " ").capitalize(),
    )


def _display_deadline(
    value: Any,
) -> str:
    raw = _text(
        value,
        "Not confirmed",
    )

    if raw == "Not confirmed":
        return raw

    try:
        parsed = datetime.fromisoformat(
            raw.replace(
                "Z",
                "+00:00",
            )
        ).astimezone(
            timezone.utc
        )

    except ValueError:
        return raw

    months = (
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec",
    )

    return (
        f"{months[parsed.month - 1]} "
        f"{parsed.day}, {parsed.year} · "
        f"{parsed.hour:02d}:"
        f"{parsed.minute:02d} UTC"
    )


def _status(
    value: Any,
) -> tuple[str, str]:

    raw = str(
        value or "WATCH"
    ).upper()

    if raw == "PROMOTE":
        return (
            "Worth pursuing",
            "promote",
        )

    if raw == "KILL":
        return (
            "Skip",
            "kill",
        )

    return (
        "Needs verification",
        "watch",
    )


def _card(
    item: dict[str, Any],
) -> str:

    raw_title = _text(
        item.get("title"),
        "Untitled opportunity",
    )

    title = escape(raw_title)

    organizer = escape(
        _text(
            item.get("organizer"),
            "Organizer not confirmed",
        )
    )

    opportunity_id = escape(
        _text(
            item.get("opportunity_id"),
            "unknown",
        ),
        quote=True,
    )

    source = _text(
        item.get(
            "canonical_source_url"
        ),
        "",
    )

    source_attr = escape(
        source,
        quote=True,
    )

    eligibility = escape(
        _text(
            item.get("eligibility")
        )
    )

    deadline = escape(
        _display_deadline(
            item.get(
                "external_deadline"
            )
        )
    )

    effort_raw = item.get(
        "estimated_effort_hours"
    )

    effort = (
        escape(str(effort_raw))
        + " hours"
        if effort_raw is not None
        else "Not estimated"
    )

    mechanism = escape(
        _text(
            item.get(
                "economic_mechanism"
            ),
            "Not confirmed",
        )
    )

    fit = escape(
        _text(
            item.get("asset_fit"),
            "Not confirmed",
        )
    )

    status_text, status_class = (
        _status(
            item.get("decision")
        )
    )

    reasons = item.get(
        "reason_codes"
    )

    if not isinstance(reasons, list):
        reasons = []

    reason_html = "".join(
        "<li>"
        + escape(_reason(code))
        + "</li>"
        for code in reasons[:4]
    )

    if not reason_html:
        reason_html = (
            "<li>No unresolved blocker "
            "is recorded in this snapshot.</li>"
        )

    actions = ""

    if source.startswith("https://"):
        actions = f'''
        <button
          class="button primary"
          type="button"
          data-investigate
          data-opportunity-id="{opportunity_id}"
          data-source-url="{source_attr}"
          data-title="{escape(raw_title, quote=True)}"
        >
          Investigate with 7-agent team
        </button>

        <a
          class="button secondary"
          href="{source_attr}"
          target="_blank"
          rel="noopener noreferrer"
        >
          View primary source
        </a>
        '''

    return f'''
    <article class="opportunity-card">

      <div class="card-top">
        <div>
          <div class="organizer">
            {organizer}
          </div>

          <h3>{title}</h3>
        </div>

        <span class="status {status_class}">
          {escape(status_text)}
        </span>
      </div>

      <div class="meta">
        <div>
          <span>Eligibility</span>
          <strong>{eligibility}</strong>
        </div>

        <div>
          <span>Deadline</span>
          <strong>{deadline}</strong>
        </div>

        <div>
          <span>Estimated human work</span>
          <strong>{effort}</strong>
        </div>
      </div>

      <div class="secondary-meta">
        <div>
          <span>Economic mechanism</span>
          <strong>{mechanism}</strong>
        </div>

        <div>
          <span>Existing asset fit</span>
          <strong>{fit}</strong>
        </div>
      </div>

      <div class="checks">
        <div class="small-label">
          What still needs checking
        </div>

        <ul>{reason_html}</ul>
      </div>

      <div class="actions">
        {actions}
      </div>

    </article>
    '''


def render_product_home(
    feed: dict[str, Any],
) -> str:

    items = feed.get("items")

    if not isinstance(items, list):
        items = []

    explicit_items = [item for item in items if isinstance(item, dict)]
    challenge_items = []
    open_items = []
    for item in explicit_items:
        try:
            candidate = adapt_explicit_feed_item(item)
        except (TypeError, ValueError):
            continue
        (challenge_items if candidate.is_contest_or_jury else open_items).append(item)

    def lane_cards(values: list[dict[str, Any]], empty: str) -> str:
        return "".join(_card(item) for item in values) or f'<div class="empty"><span>{empty}</span></div>'

    default_profile = {
        "goal": "both", "country": "Bulgaria", "available_capital": "150",
        "max_cash_spend": "0", "human_hours_per_week": "8",
        "ai_autonomy": "maximum",
        "willingness": {
            "build_business": True, "work_with_customers": False,
            "sell": False, "publish_content": False, "invest_capital": False,
            "contests_juries": True, "financial_protocols": True,
        },
        "skills_assets": [], "constraints": [],
    }
    personalized = build_product_view(default_profile, feed)
    inbox_ids = {item["candidate_id"] for item in personalized["decision_inbox"]}
    by_id = {
        str(item.get("opportunity_id") or item.get("candidate_id")): item
        for item in explicit_items
    }
    decision_cards = "".join(
        _card(by_id[item["candidate_id"]])
        for item in personalized["decision_inbox"]
        if item["candidate_id"] in inbox_ids and item["candidate_id"] in by_id
    )
    if not decision_cards:
        decision_cards = '<div class="empty"><span>No personalized recommendations meet the current limits.</span></div>'
    cards = f'''
      <section><h2>Decision Inbox</h2><div class="cards">{decision_cards}</div></section>
      <section><h2>Build &amp; Operate</h2><div class="cards"><div class="empty"><span>No evidence-backed synthesized opportunities yet.</span></div></div></section>
      <section><h2>Open Opportunities</h2><div class="cards">{lane_cards(open_items, "No open opportunities in this snapshot.")}</div></section>
      <section><h2>Challenges &amp; Competitions</h2><div class="cards">{lane_cards(challenge_items, "No challenges or competitions in this snapshot.")}</div></section>
    '''

    if not cards:
        cards = '''
        <div class="empty">
          <strong>
            No shortlisted opportunities yet.
          </strong>
          <span>
            The inbox is ready for the next Radar scan.
          </span>
        </div>
        '''

    raw_count = int(
        feed.get(
            "raw_candidate_count",
            0,
        )
        or 0
    )

    shortlist = len(items)

    watch = sum(
        1
        for item in items
        if (
            isinstance(item, dict)
            and str(
                item.get(
                    "decision",
                    "",
                )
            ).upper() == "WATCH"
        )
    )

    template = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta
  name="viewport"
  content="width=device-width, initial-scale=1"
>
<title>Autonomous Opportunity Operator</title>

<style>
:root {
  color-scheme: dark;
  --bg: #07090f;
  --panel: rgba(15,19,30,.82);
  --line: rgba(255,255,255,.10);
  --text: #f6f8ff;
  --muted: #929bb0;
  --blue: #8daeff;
  --violet: #c1abff;
  --green: #6ee7b7;
  --amber: #ffd27d;
  --red: #ff9aa7;
  --shadow: 0 28px 90px rgba(0,0,0,.34);
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  min-height: 100vh;
  color: var(--text);
  background:
    radial-gradient(
      circle at 12% -5%,
      rgba(75,112,255,.21),
      transparent 32%
    ),
    radial-gradient(
      circle at 91% 3%,
      rgba(178,117,255,.14),
      transparent 27%
    ),
    linear-gradient(
      180deg,
      #07090f,
      #0a0d14 54%,
      #07090f
    );
  font-family:
    Inter,
    ui-sans-serif,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}

button,
input {
  font: inherit;
}

.shell {
  width: min(1440px, calc(100% - 40px));
  margin: 0 auto;
  padding: 27px 0 70px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 22px;
  margin-bottom: 50px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 780;
}

.mark {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.17);
  background:
    linear-gradient(
      135deg,
      rgba(141,174,255,.25),
      rgba(193,171,255,.12)
    );
}

.nav {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}

.nav a {
  padding: 9px 12px;
  border-radius: 10px;
  color: #aeb7ca;
  text-decoration: none;
  font-size: 12px;
}

.nav a:hover {
  color: white;
  background: rgba(255,255,255,.04);
}

.nav .proof {
  border: 1px solid var(--line);
}

.hero {
  display: grid;
  grid-template-columns:
    minmax(0,1.25fr)
    minmax(340px,.75fr);
  gap: 20px;
}

.hero-main,
.snapshot {
  border: 1px solid var(--line);
  border-radius: 28px;
  background:
    linear-gradient(
      145deg,
      rgba(20,25,40,.90),
      rgba(11,14,23,.72)
    );
  box-shadow: var(--shadow);
}

.hero-main {
  padding: 46px;
}

.kicker {
  color: #cad6ff;
  text-transform: uppercase;
  letter-spacing: .13em;
  font-size: 10px;
  font-weight: 820;
}

h1 {
  max-width: 860px;
  margin: 18px 0 0;
  font-size: clamp(49px,5.1vw,78px);
  line-height: .96;
  letter-spacing: -.063em;
}

h1 span {
  background:
    linear-gradient(
      90deg,
      #91b0ff,
      #d3b5ff
    );
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.hero-main p {
  max-width: 760px;
  margin: 25px 0 0;
  color: #b7c0d2;
  font-size: 18px;
  line-height: 1.65;
}

.no-signup {
  display: inline-flex;
  margin-top: 22px;
  padding: 9px 12px;
  border: 1px solid rgba(110,231,183,.16);
  border-radius: 999px;
  color: #d0efe3;
  background: rgba(110,231,183,.055);
  font-size: 12px;
}

.discover-box {
  margin-top: 24px;
  padding: 15px;
  border: 1px solid rgba(141,174,255,.18);
  border-radius: 15px;
  background: rgba(141,174,255,.04);
}

.discover-copy strong {
  display: block;
  font-size: 13px;
}

.discover-copy span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.45;
}

.discover-controls {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  margin-top: 12px;
}

.discover-controls input {
  width: 100%;
  padding: 11px 12px;
  outline: none;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 11px;
  background: rgba(5,7,12,.64);
}

.discover-button {
  padding: 11px 14px;
  border: 0;
  border-radius: 11px;
  color: #08101f;
  background:
    linear-gradient(
      90deg,
      #91b0ff,
      #c0acff
    );
  font-weight: 760;
  cursor: pointer;
}

.discover-button:disabled {
  opacity: .55;
  cursor: not-allowed;
}

.discover-status {
  min-height: 14px;
  margin-top: 7px;
  color: #aab5ca;
  font-size: 9px;
}

.snapshot {
  padding: 28px;
}

.snapshot-label,
.section-label,
.small-label {
  text-transform: uppercase;
  letter-spacing: .10em;
  font-size: 9px;
  font-weight: 820;
}

.snapshot-label {
  color: var(--green);
}

.snapshot h2 {
  margin: 11px 0 0;
  font-size: 25px;
  letter-spacing: -.04em;
}

.snapshot p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
  margin-top: 20px;
}

.stat {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: rgba(255,255,255,.024);
}

.stat strong {
  display: block;
  font-size: 25px;
}

.stat span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 9px;
}

.how {
  margin-top: 20px;
  padding: 23px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--panel);
}

.how-head h2 {
  margin: 6px 0 0;
  font-size: 23px;
}

.how-grid {
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 11px;
  margin-top: 16px;
}

.how-card {
  padding: 17px;
  border: 1px solid var(--line);
  border-radius: 15px;
  background: rgba(255,255,255,.022);
}

.how-card b {
  color: var(--blue);
  font-size: 10px;
}

.how-card strong {
  display: block;
  margin-top: 8px;
  font-size: 13px;
}

.how-card span {
  display: block;
  margin-top: 5px;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.5;
}

.workspace {
  display: grid;
  grid-template-columns: 310px 1fr;
  gap: 20px;
  margin-top: 20px;
  align-items: start;
}

.profile,
.inbox {
  border: 1px solid var(--line);
  border-radius: 23px;
  background: var(--panel);
}

.profile {
  position: sticky;
  top: 18px;
  padding: 23px;
}

.section-label {
  color: var(--muted);
}

.profile h2,
.inbox h2 {
  margin: 7px 0 0;
  font-size: 22px;
}

.profile-copy {
  margin: 8px 0 17px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.field {
  margin-top: 12px;
}

.field label {
  display: block;
  margin-bottom: 6px;
  color: #bac3d5;
  font-size: 10px;
}

.field input {
  width: 100%;
  padding: 11px 12px;
  outline: none;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 11px;
  background: rgba(5,7,12,.64);
}

.field input:focus {
  border-color: rgba(141,174,255,.55);
  box-shadow: 0 0 0 3px rgba(141,174,255,.07);
}

.safety-note {
  margin-top: 15px;
  padding: 12px;
  border: 1px solid rgba(255,210,125,.13);
  border-radius: 12px;
  color: #d2c9ad;
  background: rgba(255,210,125,.035);
  font-size: 10px;
  line-height: 1.5;
}

.inbox {
  padding: 24px;
}

.inbox-head {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 15px;
  margin-bottom: 16px;
}

.inbox-subtitle,
.inbox-count {
  color: var(--muted);
  font-size: 10px;
}

.inbox-subtitle {
  margin-top: 6px;
}

.cards {
  display: grid;
  gap: 13px;
}

.opportunity-card {
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 17px;
  background:
    linear-gradient(
      145deg,
      rgba(255,255,255,.034),
      rgba(255,255,255,.016)
    );
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}

.organizer {
  color: var(--muted);
  font-size: 10px;
}

.opportunity-card h3 {
  max-width: 850px;
  margin: 6px 0 0;
  font-size: 18px;
  line-height: 1.3;
}

.status {
  height: fit-content;
  flex: 0 0 auto;
  padding: 7px 9px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: .07em;
  font-size: 8px;
  font-weight: 820;
}

.status.watch {
  color: var(--amber);
  border: 1px solid rgba(255,210,125,.18);
  background: rgba(255,210,125,.05);
}

.status.promote {
  color: var(--green);
  border: 1px solid rgba(110,231,183,.18);
  background: rgba(110,231,183,.05);
}

.status.kill {
  color: var(--red);
  border: 1px solid rgba(255,154,167,.18);
  background: rgba(255,154,167,.05);
}

.meta {
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 9px;
  margin-top: 16px;
}

.secondary-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
  margin-top: 9px;
}

.meta div,
.secondary-meta div {
  padding: 11px;
  border: 1px solid rgba(255,255,255,.07);
  border-radius: 11px;
  background: rgba(255,255,255,.017);
}

.meta span,
.secondary-meta span {
  display: block;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .06em;
  font-size: 8px;
}

.meta strong,
.secondary-meta strong {
  display: block;
  margin-top: 5px;
  font-size: 11px;
  line-height: 1.4;
}

.checks {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid rgba(255,210,125,.10);
  border-radius: 11px;
  background: rgba(255,210,125,.025);
}

.small-label {
  color: #bbae8d;
}

.checks ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #c6cddb;
  font-size: 10px;
  line-height: 1.55;
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.button {
  padding: 10px 13px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 740;
  cursor: pointer;
  text-decoration: none;
}

.button.primary {
  border: 0;
  color: #08101f;
  background:
    linear-gradient(
      90deg,
      #91b0ff,
      #c0acff
    );
}

.button.secondary {
  color: #d6ddec;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.035);
}

.button:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.result {
  display: none;
  margin-top: 20px;
  padding: 20px;
  border: 1px solid rgba(141,174,255,.18);
  border-radius: 16px;
  background: rgba(141,174,255,.035);
}

.result.visible {
  display: block;
}

.result h3 {
  margin: 6px 0 0;
  font-size: 22px;
}

.result-copy {
  margin-top: 10px;
  color: #c1c9d9;
  font-size: 11px;
  line-height: 1.55;
}

.result-reasons {
  margin-top: 10px;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.55;
}

.result-boundary {
  margin-top: 12px;
  padding: 11px;
  border: 1px solid rgba(255,210,125,.13);
  border-radius: 10px;
  color: #d7ceb3;
  background: rgba(255,210,125,.035);
  font-size: 10px;
}

.empty {
  padding: 45px;
  text-align: center;
  color: var(--muted);
}

.empty strong,
.empty span {
  display: block;
}

.empty span {
  margin-top: 6px;
}

.footer {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-top: 25px;
  padding: 17px 3px 0;
  color: #717a8d;
  font-size: 9px;
}

@media (max-width: 1000px) {
  .hero,
  .workspace {
    grid-template-columns: 1fr;
  }

  .profile {
    position: static;
  }

  .how-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 650px) {
  .shell {
    width: min(100% - 22px, 1440px);
    padding-top: 17px;
  }

  .topbar,
  .inbox-head,
  .footer,
  .card-top {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-main {
    padding: 29px 23px;
  }

  h1 {
    font-size: 44px;
  }

  .stats,
  .meta,
  .secondary-meta,
  .discover-controls {
    grid-template-columns: 1fr;
  }
}

/* PHASE 4I-R2 — UNIFIED FRONT DOOR */

.topbar {
  margin-bottom: 22px;
}

.hero.frontdoor {
  display: grid;
  grid-template-columns:
    minmax(0, .86fr)
    minmax(600px, 1.14fr);
  gap: 30px;
  align-items: center;
  padding: 28px 30px;
  border: 1px solid var(--line);
  border-radius: 28px;
  background:
    linear-gradient(
      145deg,
      rgba(20,25,40,.91),
      rgba(11,14,23,.74)
    );
  box-shadow: var(--shadow);
}

.frontdoor-copy {
  min-width: 0;
  padding: 5px 4px;
}

.frontdoor-copy h1 {
  max-width: 660px;
  margin: 14px 0 15px;
  font-size: clamp(43px, 4vw, 61px);
  line-height: .98;
  letter-spacing: -.052em;
}

.frontdoor-copy p {
  max-width: 650px;
  margin: 0;
  color: #bdc7da;
  font-size: 14px;
  line-height: 1.58;
}

.frontdoor-capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 17px;
}

.frontdoor-capabilities span {
  padding: 7px 9px;
  border: 1px solid rgba(141,174,255,.16);
  border-radius: 999px;
  background: rgba(141,174,255,.045);
  color: #c7d3ee;
  font-size: 9px;
}

.frontdoor-copy .no-signup {
  margin-top: 14px;
  padding: 7px 10px;
  font-size: 10px;
}

.frontdoor-profile {
  padding: 20px 21px;
  border: 1px solid rgba(255,255,255,.09);
  border-radius: 19px;
  background: rgba(4,7,13,.38);
}

.frontdoor-profile h2 {
  margin: 5px 0 4px;
  font-size: 21px;
}

.frontdoor-profile .profile-copy {
  max-width: 720px;
  margin: 4px 0 12px;
  font-size: 10px;
}

.profile-grid {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 9px 11px;
}

.frontdoor-profile .field {
  margin-top: 0;
}

.frontdoor-profile .field label {
  min-height: 22px;
  margin-bottom: 4px;
  font-size: 9px;
}

.frontdoor-profile .field input {
  padding: 9px 10px;
  font-size: 11px;
}

.frontdoor-cta {
  width: 100%;
  margin-top: 13px;
  padding: 12px 15px;
  font-size: 13px;
}

.frontdoor-safety {
  margin-top: 7px;
  padding: 8px 10px;
  font-size: 8px;
  line-height: 1.4;
}

.workspace.results-workspace {
  display: block;
  margin-top: 20px;
}

.results-workspace .inbox {
  width: 100%;
}

.radar-strip {
  display: grid;
  grid-template-columns:
    minmax(260px, .72fr)
    minmax(0, 1.28fr);
  gap: 20px;
  align-items: center;
  margin-top: 20px;
  padding: 17px 20px;
  border-radius: 20px;
  box-shadow: none;
}

.radar-strip h2 {
  margin-top: 5px;
  font-size: 17px;
}

.radar-strip p {
  max-width: 520px;
  margin-top: 4px;
  font-size: 9px;
}

.radar-strip .stats {
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 0;
}

.radar-strip .stat {
  padding: 10px 11px;
}

.radar-strip .stat strong {
  font-size: 19px;
}

@media (max-width: 1120px) {
  .hero.frontdoor {
    grid-template-columns: 1fr;
  }

  .profile-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .radar-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 650px) {
  .hero.frontdoor {
    padding: 22px 20px;
    gap: 22px;
  }

  .frontdoor-copy h1 {
    max-width: none;
    font-size: 40px;
  }

  .frontdoor-profile {
    padding: 18px;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }

  .radar-strip .stats {
    grid-template-columns: 1fr 1fr;
  }
}


/* PHASE 4J-A — FIRST-FOLD PRODUCT POLISH */

button,
input,
select {
  font: inherit;
}

.frontdoor-profile .profile-copy {
  margin-top: 6px;
  margin-bottom: 14px;
  font-size: 11px;
  line-height: 1.5;
}

.frontdoor-profile .field label {
  min-height: 24px;
  margin-bottom: 5px;
  color: #c7cfdf;
  font-size: 10px;
  line-height: 1.25;
}

.frontdoor-profile .field input,
.frontdoor-profile .field select {
  width: 100%;
  min-height: 39px;
  padding: 9px 10px;
  outline: none;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 11px;
  background: rgba(5,7,12,.64);
  font-size: 11px;
}

.frontdoor-profile .field select {
  cursor: pointer;
}

.frontdoor-profile .field input::placeholder {
  color: #697389;
}

.frontdoor-profile .field input:focus,
.frontdoor-profile .field select:focus {
  border-color: rgba(141,174,255,.55);
  box-shadow: 0 0 0 3px rgba(141,174,255,.07);
}

.frontdoor-safety {
  margin-top: 9px;
  padding: 9px 10px;
  font-size: 9px;
  line-height: 1.45;
}

.results-pending {
  padding: 24px 26px;
  border: 1px solid rgba(141,174,255,.12);
  border-radius: 16px;
  background:
    linear-gradient(
      135deg,
      rgba(141,174,255,.045),
      rgba(193,171,255,.025)
    );
}

.results-pending h2 {
  max-width: 760px;
  margin: 7px 0 0;
  font-size: 22px;
  letter-spacing: -.025em;
}

.results-pending p {
  max-width: 720px;
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.55;
}

[hidden] {
  display: none !important;
}

</style>
</head>

<body>
<div class="shell">

  <header class="topbar">
    <div class="brand">
      <div class="mark">A</div>
      <div>Autonomous Opportunity Operator</div>
    </div>

    <nav class="nav">
      <a href="#inbox">Opportunity Inbox</a>
      <a href="#how">How it works</a>
      <a href="/judge-console" class="proof">
        Technical proof
      </a>
    </nav>
  </header>

  <section class="hero frontdoor" id="frontdoor">

    <div class="frontdoor-copy">

      <div class="kicker">
        Autonomous discovery &amp; analysis · permissioned execution
      </div>

      <h1>
        Find what AI can
        <span>build, operate, or pursue for you.</span>
      </h1>

      <p>
        Tell AOO your goal, resources and limits.
        It discovers opportunities that already exist,
        synthesizes ideas no one posted,
        and investigates the promising few.
      </p>

      <div class="frontdoor-capabilities">
        <span>Discovers explicit opportunities</span>
        <span>Synthesizes latent opportunities</span>
        <span>Investigates with 7 agents</span>
      </div>

      <div class="no-signup">
        ✓ No sign-up needed to explore this demo
      </div>

    </div>

    <div class="frontdoor-profile">

      <form id="profileForm">

        <div class="section-label">
          Decision profile · Start here
        </div>

        <h2>What should AOO work with?</h2>

        <div class="profile-copy">
          Your profile is the primary query.
          Change the defaults to match your situation.
          It is not registration and authorizes no external action.
        </div>

        <div class="profile-grid">

          <div class="field">
            <label for="goal">
              What do you want more of?
            </label>
            <select id="goal">
              <option value="both" selected>
                Income + free time
              </option>
              <option value="income">
                Income
              </option>
              <option value="free_time">
                Free time
              </option>
            </select>
          </div>

          <div class="field">
            <label for="jurisdiction">
              Country / Jurisdiction
            </label>
            <input
              id="jurisdiction"
              placeholder="e.g. Bulgaria"
              autocomplete="country-name"
              required
            >
          </div>

          <div class="field">
            <label for="capital">
              Available capital (€)
            </label>
            <input
              id="capital"
              type="number"
              min="0"
              step="1"
              placeholder="e.g. 150"
              required
            >
          </div>

          <div class="field">
            <label for="cashSpend">
              Max pursuit budget (€)
            </label>
            <input
              id="cashSpend"
              type="number"
              min="0"
              step="1"
              value="0"
            >
          </div>

          <div class="field">
            <label for="humanHours">
              Max human hours / week
            </label>
            <input
              id="humanHours"
              type="number"
              min="0"
              step="0.5"
              placeholder="e.g. 5"
              required
            >
          </div>

          <div class="field">
            <label for="autonomy">
              Desired AI autonomy
            </label>
            <select id="autonomy">
              <option value="maximum" selected>
                Maximum
              </option>
              <option value="balanced">
                Balanced
              </option>
              <option value="assistive">
                Assistive
              </option>
            </select>
          </div>

        </div>

        <button
          type="submit"
          class="discover-button frontdoor-cta"
          aria-label="Personalize opportunities"
        >
          Find what AI can do for me
        </button>

        <div
          class="discover-status"
          id="profileStatus"
        ></div>

        <div class="safety-note frontdoor-safety">
          Profile settings do not authorize registration,
          spending, submissions, identity representation,
          wallet activity or other consequential external action.
        </div>

      </form>

    </div>

  </section>

  <section class="workspace results-workspace">

    <main class="inbox" id="inbox">

      <div
        class="results-pending"
        id="resultsPending"
      >
        <div class="section-label">
          Ready to evaluate
        </div>

        <h2>
          __SHORTLIST__ shortlisted candidates are waiting for your profile.
        </h2>

        <p>
          Run AOO above. It will apply your limits,
          rank what fits, and show only the opportunities
          that deserve your attention.
        </p>
      </div>

      <div id="resultsContent" hidden>

      <div class="inbox-head">
        <div>
          <div class="section-label">
            Opportunity Inbox
          </div>

          <h2>What deserves attention now</h2>

          <div class="inbox-subtitle">
            Real candidates from the stored Radar shortlist.
          </div>
        </div>

        <div class="inbox-count">
          __SHORTLIST__ shortlisted
        </div>
      </div>

      <div id="productLanes">
        __CARDS__
      </div>

      <section class="result" id="resultPanel">

        <div class="section-label">
          Deep analysis
        </div>

        <h3 id="resultTitle">—</h3>

        <div
          class="result-copy"
          id="resultDisposition"
        ></div>

        <div
          class="result-reasons"
          id="resultReasons"
        ></div>

        <div class="result-boundary">
          Human approval remains mandatory before any
          consequential external action.
        </div>

      </section>

      </div>

    </main>

  </section>

  <aside class="snapshot radar-strip">

    <div class="radar-strip-copy">

      <div class="snapshot-label">
        Latest stored Radar snapshot
      </div>

      <h2>
        __SHORTLIST__ opportunities need attention
      </h2>

      <p>
        These are real shortlisted candidates from the
        existing Radar. This page does not pretend that a
        fresh internet discovery scan has just occurred.
      </p>

    </div>

    <div class="stats">

      <div class="stat">
        <strong>__RAW__</strong>
        <span>candidates evaluated</span>
      </div>

      <div class="stat">
        <strong>__SHORTLIST__</strong>
        <span>shortlisted</span>
      </div>

      <div class="stat">
        <strong>__WATCH__</strong>
        <span>need verification</span>
      </div>

      <div class="stat">
        <strong>0</strong>
        <span>external actions taken</span>
      </div>

    </div>

  </aside>

  <div class="discover-box">
          <div class="discover-copy">
            <strong>Advanced search</strong>
            <span>
              Search official public sources now.
              This discovery step uses no Gemini model.
            </span>
          </div>

          <div class="discover-controls">
            <input
              id="searchTerms"
              value="AI agents, automation, API"
              aria-label="Opportunity search terms"
            >

            <button
              id="refreshButton"
              type="button"
              class="discover-button"
            >
              Find new opportunities
            </button>
          </div>

          <div
            class="discover-status"
            id="discoverStatus"
          ></div>
        </div>

  <section class="how" id="how">

    <div class="how-head">
      <div class="section-label">
        How opportunities get here
      </div>

      <h2>
        The system narrows the field before asking for your attention.
      </h2>
    </div>

    <div class="how-grid">

      <div class="how-card">
        <b>01</b>
        <strong>Radar screens candidates</strong>
        <span>
          Opportunity candidates are collected, normalized
          and cheaply screened before entering your inbox.
        </span>
      </div>

      <div class="how-card">
        <b>02</b>
        <strong>You see the unresolved few</strong>
        <span>
          Eligibility, deadlines, human effort and known
          blockers are visible before deep analysis.
        </span>
      </div>

      <div class="how-card">
        <b>03</b>
        <strong>Agents investigate when useful</strong>
        <span>
          One explicit click starts the seven-agent workflow.
          It can investigate, but cannot register, spend or
          submit without human approval.
        </span>
      </div>

    </div>

  </section>

  <footer class="footer">
    <span>
      Autonomous Opportunity Operator
    </span>

    <span>
      Architecture and verified runtime evidence are available
      under “Technical proof”.
    </span>
  </footer>

</div>

<script>
(() => {
  "use strict";

  const q = (id) =>
    document.getElementById(id);

  function humanReason(code) {
    return String(code || "")
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(
        /^./,
        (x) => x.toUpperCase()
      );
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function personalizedCard(item) {
    const source = String(item.source_url || "");
    const id = escapeHtml(item.candidate_id || "unknown");
    const title = escapeHtml(item.title || "Untitled opportunity");
    const reasons = Array.isArray(item.reason_codes) && item.reason_codes.length
      ? item.reason_codes.map((code) => "<li>" + escapeHtml(humanReason(code)) + "</li>").join("")
      : "<li>No unresolved blocker is recorded in this snapshot.</li>";
    const actions = source.startsWith("https://")
      ? '<button class="button primary" type="button" data-investigate data-opportunity-id="'
        + id + '" data-source-url="' + escapeHtml(source) + '" data-title="' + title
        + '">Investigate with 7-agent team</button> '
        + '<a class="button secondary" href="' + escapeHtml(source)
        + '" target="_blank" rel="noopener noreferrer">View primary source</a>'
      : "";
    return '<article class="opportunity-card"><div class="card-top"><div><div class="organizer">'
      + escapeHtml(item.origin || "opportunity") + '</div><h3>' + title
      + '</h3></div><span class="status watch">' + escapeHtml(item.fit_band || "Needs verification")
      + '</span></div><div class="meta"><div><span>Eligibility</span><strong>'
      + escapeHtml(item.applicant_feasibility || "UNKNOWN")
      + '</strong></div><div><span>Required capital</span><strong>'
      + escapeHtml(item.capital_required == null ? "Not confirmed" : item.capital_required)
      + '</strong></div><div><span>Estimated human work</span><strong>'
      + escapeHtml(item.human_work_hours == null ? "Not estimated" : item.human_work_hours + " hours")
      + '</strong></div></div><div class="checks"><div class="small-label">What still needs checking</div><ul>'
      + reasons + '</ul></div><div class="actions">' + actions + '</div></article>';
  }

  function renderProductView(view) {
    const lanes = [
      ["decision_inbox", "Decision Inbox", "No personalized recommendations meet the current limits."],
      ["build_operate", "Build &amp; Operate", "No evidence-backed synthesized opportunities yet."],
      ["open_opportunities", "Open Opportunities", "No open opportunities meet this view."],
      ["challenges_competitions", "Challenges &amp; Competitions", "No challenges or competitions meet this view."]
    ];
    q("productLanes").innerHTML = lanes.map(([key, label, empty]) => {
      const items = Array.isArray(view[key]) ? view[key] : [];
      const cards = items.length
        ? items.map(personalizedCard).join("")
        : '<div class="empty"><span>' + escapeHtml(empty) + '</span></div>';
      return "<section><h2>" + label + '</h2><div class="cards">' + cards + "</div></section>";
    }).join("");
    bindInvestigationButtons();
  }

  async function personalize(event) {
    event.preventDefault();
    const status = q("profileStatus");
    status.textContent = "Applying deterministic personalization…";
    const payload = {
      goal: q("goal").value.trim(),
      country: q("jurisdiction").value.trim(),
      available_capital: q("capital").value.trim(),
      max_cash_spend: q("cashSpend").value.trim(),
      human_hours_per_week: q("humanHours").value.trim(),
      ai_autonomy: q("autonomy").value.trim(),
      willingness: {
        build_business: true,
        work_with_customers: false,
        sell: false,
        publish_content: false,
        invest_capital: false,
        contests_juries: true,
        financial_protocols: true
      },
      skills_assets: [],
      constraints: []
    };
    try {
      const response = await fetch("/opportunities/personalized", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok || data.status === "INVALID") {
        throw new Error("The profile is invalid; check the supplied limits.");
      }
      renderProductView(data);

      q("resultsPending").hidden = true;
      q("resultsContent").hidden = false;

      status.textContent = "Personalized view updated.";

      q("inbox").scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    } catch (error) {
      status.textContent = String(error.message || error);
    }
  }

  async function refreshDiscovery() {

    const button =
      q("refreshButton");

    const status =
      q("discoverStatus");

    const terms =
      q("searchTerms").value.trim();

    const original =
      button.textContent;

    button.disabled = true;

    button.textContent =
      "Scanning official sources…";

    status.textContent =
      "Checking current public opportunity sources.";

    try {
      const response = await fetch(
        "/discover/refresh",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json"
          },
          body: JSON.stringify({
            search_terms: terms
          })
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          "Discovery returned HTTP "
          + response.status
        );
      }

      if (data.status === "FAIL") {
        throw new Error(
          "All discovery sources failed"
        );
      }

      status.textContent =
        String(
          data.shortlist_count || 0
        )
        + " fresh candidates found. "
        + "Refreshing inbox…";

      window.location.reload();

    } catch (error) {

      status.textContent =
        "Discovery did not complete: "
        + String(
            error.message
            || error
          );

      button.disabled = false;
      button.textContent = original;
    }
  }

  async function investigate(button) {

    const source =
      button.dataset.sourceUrl || "";

    const opportunityId =
      button.dataset.opportunityId || "";

    const title =
      button.dataset.title || "Opportunity";

    if (!source.startsWith("https://")) {
      return;
    }

    const original =
      button.textContent;

    button.disabled = true;
    button.textContent =
      "Agent team investigating…";

    const panel =
      q("resultPanel");

    panel.classList.add("visible");

    q("resultTitle").textContent =
      title;

    q("resultDisposition").textContent =
      "The seven-agent team is checking the primary source and your constraints. No external action is being taken.";

    q("resultReasons").textContent =
      "";

    panel.scrollIntoView({
      behavior: "smooth",
      block: "nearest"
    });

    try {
      const response = await fetch(
        "/decision/primary-source",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json"
          },
          body: JSON.stringify({
            source_url: source,

            opportunity_id: opportunityId,

            decision_profile: {
              operator_jurisdiction:
                q("jurisdiction").value.trim(),

              available_capital:
                q("capital").value.trim(),

              max_cash_spend:
                q("cashSpend").value.trim(),

              max_human_hours:
                q("humanHours").value.trim(),

              objective:
                "Determine whether this opportunity merits further human attention under the supplied constraints; do not register, submit, spend money, represent the operator, or take consequential external action."
            }
          })
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          "Analysis returned HTTP "
          + response.status
        );
      }

      const outcome =
        data.outcome || {};

      const disposition =
        outcome.disposition
        || data.status
        || "UNKNOWN";

      q("resultDisposition").textContent =
        "Decision: "
        + disposition.replaceAll(
            "_",
            " "
          );

      const reasons =
        outcome.reason_codes
        || data.reason_codes
        || [];

      q("resultReasons").textContent =
        reasons.length
        ? reasons
            .map(humanReason)
            .join(" · ")
        : "No unresolved reason codes returned.";

    } catch (error) {

      q("resultDisposition").textContent =
        "Analysis did not complete.";

      q("resultReasons").textContent =
        String(
          error.message || error
        );

    } finally {

      button.disabled = false;
      button.textContent = original;
    }
  }

  q("refreshButton")
    .addEventListener(
      "click",
      refreshDiscovery
    );

  function bindInvestigationButtons() {
    document.querySelectorAll("[data-investigate]").forEach((button) => {
      button.addEventListener("click", () => investigate(button));
    });
  }

  q("profileForm").addEventListener("submit", personalize);
  bindInvestigationButtons();
})();
</script>

</body>
</html>
'''

    return (
        template
        .replace(
            "__CARDS__",
            cards,
        )
        .replace(
            "__RAW__",
            escape(str(raw_count)),
        )
        .replace(
            "__SHORTLIST__",
            escape(str(shortlist)),
        )
        .replace(
            "__WATCH__",
            escape(str(watch)),
        )
    )

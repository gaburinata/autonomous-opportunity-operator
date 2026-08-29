"""Simple public V5 product front door."""

from __future__ import annotations


def render_public_v5_home() -> str:

    return r'''<!doctype html>
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
  --bg: #080a10;
  --panel: #111620;
  --panel2: #171d29;
  --line: rgba(255,255,255,.12);
  --text: #f6f8ff;
  --muted: #b8c0d0;
  --accent: #a9bfff;
  --good: #83e6bb;
  --warn: #ffd78a;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background:
    radial-gradient(
      circle at 15% 0,
      rgba(86,115,255,.16),
      transparent 30%
    ),
    var(--bg);
  color: var(--text);
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    "Segoe UI",
    sans-serif;
  font-size: 18px;
  line-height: 1.55;
}

button,
input,
select {
  font: inherit;
}

a {
  color: var(--accent);
}

.shell {
  width: min(1080px, calc(100% - 36px));
  margin: 0 auto;
  padding: 26px 0 70px;
}

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 42px;
}

.brand {
  font-weight: 800;
  font-size: 18px;
}

.proof {
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  text-decoration: none;
  font-size: 16px;
}

.hero {
  max-width: 900px;
}

.kicker {
  color: var(--good);
  font-size: 16px;
  font-weight: 800;
}

h1 {
  margin: 12px 0 0;
  font-size: clamp(42px, 6vw, 68px);
  line-height: 1.02;
  letter-spacing: -.045em;
}

.hero-copy {
  max-width: 830px;
  margin-top: 22px;
  color: var(--muted);
  font-size: 20px;
  line-height: 1.6;
}

.hero-copy strong {
  color: var(--text);
}

.profile {
  margin-top: 36px;
  padding: 30px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: rgba(17,22,32,.93);
}

.profile h2 {
  margin: 0;
  font-size: 30px;
}

.profile-intro {
  margin: 8px 0 26px;
  color: var(--muted);
  font-size: 17px;
}

.grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0,1fr));
  gap: 20px;
}

.field label {
  display: block;
  margin-bottom: 8px;
  font-weight: 750;
  font-size: 17px;
}

.help {
  display: block;
  margin-top: 7px;
  color: var(--muted);
  font-size: 16px;
}

.field input,
.field select {
  width: 100%;
  min-height: 52px;
  padding: 11px 13px;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #0c111a;
  font-size: 18px;
}

.money-row {
  display: grid;
  grid-template-columns: 1fr 145px;
  gap: 10px;
}

.citizenships {
  display: grid;
  gap: 9px;
}

.add-citizenship {
  width: fit-content;
  margin-top: 8px;
  padding: 8px 0;
  border: 0;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  font-size: 16px;
}

details {
  margin-top: 24px;
  padding: 17px 18px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255,255,255,.02);
}

summary {
  cursor: pointer;
  font-weight: 750;
  font-size: 17px;
}

.exclusions {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.check {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  font-size: 17px;
}

.check input {
  margin-top: 6px;
  transform: scale(1.2);
}

.primary {
  width: 100%;
  margin-top: 24px;
  min-height: 58px;
  border: 0;
  border-radius: 14px;
  color: #09111e;
  background:
    linear-gradient(
      90deg,
      #9bb8ff,
      #c9b2ff
    );
  font-size: 19px;
  font-weight: 850;
  cursor: pointer;
}

.primary:disabled {
  opacity: .6;
  cursor: wait;
}

.safety {
  margin-top: 14px;
  color: var(--muted);
  font-size: 16px;
}

.status {
  min-height: 28px;
  margin-top: 14px;
  font-size: 17px;
}

.results {
  margin-top: 42px;
}

.results[hidden] {
  display: none;
}

.results h2 {
  margin: 0;
  font-size: 34px;
}

.results-intro {
  margin-top: 7px;
  color: var(--muted);
  font-size: 17px;
}

.cards {
  display: grid;
  gap: 20px;
  margin-top: 22px;
}

.card {
  padding: 26px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--panel);
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.category {
  color: var(--good);
  font-size: 16px;
  font-weight: 800;
}

.card h3 {
  margin: 5px 0 0;
  font-size: 26px;
  line-height: 1.25;
}

.verdict {
  flex: 0 0 auto;
  padding: 7px 11px;
  border: 1px solid rgba(255,215,138,.23);
  border-radius: 999px;
  color: var(--warn);
  font-size: 15px;
  font-weight: 800;
}

.why {
  margin-top: 17px;
  color: #d4daea;
  font-size: 18px;
}

.metrics {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0,1fr));
  gap: 12px;
  margin-top: 19px;
}

.metric {
  padding: 15px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: var(--panel2);
}

.metric span {
  display: block;
  color: var(--muted);
  font-size: 16px;
}

.metric strong {
  display: block;
  margin-top: 4px;
  font-size: 18px;
}

.checking {
  margin-top: 19px;
}

.checking strong {
  font-size: 17px;
}

.checking ul {
  margin: 9px 0 0;
  padding-left: 23px;
  color: #d1d7e5;
  font-size: 17px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}

.action {
  padding: 10px 13px;
  border: 1px solid var(--line);
  border-radius: 11px;
  text-decoration: none;
  font-size: 16px;
}

.effects,
.notice,
.empty {
  margin-top: 20px;
  padding: 19px;
  border: 1px solid var(--line);
  border-radius: 15px;
  background: rgba(255,255,255,.025);
  color: var(--muted);
  font-size: 17px;
}

.effects strong,
.notice strong,
.empty strong {
  color: var(--text);
}

.effects ul {
  margin: 9px 0 0;
}

.footer {
  margin-top: 45px;
  padding-top: 22px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 16px;
}

@media (max-width: 760px) {
  .grid,
  .metrics {
    grid-template-columns: 1fr;
  }

  .money-row {
    grid-template-columns: 1fr 120px;
  }

  .profile {
    padding: 22px;
  }

  .card-top,
  .top {
    flex-direction: column;
  }
}
</style>
</head>

<body>
<div class="shell">

  <header class="top">
    <div class="brand">
      Autonomous Opportunity Operator
    </div>

    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
      <a
        class="proof"
        href="#frontdoor"
      >
        Start here
      </a>

      <a
        class="proof"
        href="/judge-console"
      >
        Technical proof
      </a>
    </div>
  </header>

  <main>

    <section class="hero" id="frontdoor">
      <div class="kicker">
        Public judge demo · Start here
      </div>

      <h1>
        Let AI find ways to make you
        money or save you time.
      </h1>

      <div class="hero-copy">
        <strong>
          This is the Autonomous Opportunity Operator.
        </strong>
        Tell it what you have and what your limits are.
        AOO looks for opportunities where AI can do
        most or all of the research, building, testing,
        preparation or operation for you.
      </div>
    </section>

    <section class="profile">
      <h2>Tell AOO about your situation</h2>

      <p class="profile-intro">
        Anything legal is considered by default.
        Traditional jobs are not the goal:
        AOO looks for opportunities where AI can do
        most of the actual work.
      </p>

      <form id="profileForm">

        <div class="grid">

          <div class="field">
            <label for="goal">
              What do you want?
            </label>

            <select id="goal" required>
              <option value="both">
                More income + more free time
              </option>
              <option value="income">
                More income
              </option>
              <option value="time">
                More free time
              </option>
            </select>
          </div>

          <div class="field">
            <label for="residence">
              Where do you legally live?
            </label>

            <select
              id="residence"
              required
            ></select>

            <span class="help">
              Used for platform, legal and opportunity eligibility.
            </span>
          </div>

          <div class="field">
            <label>
              Citizenship
            </label>

            <div
              class="citizenships"
              id="citizenships"
            ></div>

            <button
              type="button"
              class="add-citizenship"
              id="addCitizenship"
            >
              + Add another citizenship
            </button>

            <span class="help">
              Some grants, contests, platforms and financial
              services restrict citizenship separately from residence.
            </span>
          </div>

          <div class="field">
            <label for="availableMoney">
              Money AOO can work with
            </label>

            <div class="money-row">
              <input
                id="availableMoney"
                type="number"
                min="0"
                step="0.01"
                placeholder="150"
                required
              >

              <select
                id="currency"
                required
                aria-label="Currency"
              ></select>
            </div>

            <span class="help">
              Choose the actual currency or liquid asset.
            </span>
          </div>

          <div class="field">
            <label for="maxSpend">
              Max cash AOO may spend or put at risk
            </label>

            <input
              id="maxSpend"
              type="number"
              min="0"
              step="0.01"
              placeholder="25"
              required
            >

            <span class="help">
              This is your maximum cost/risk — not the amount
              you hope to earn.
            </span>
          </div>

          <div class="field">
            <label for="hours">
              How much of your time can it use each week?
            </label>

            <input
              id="hours"
              type="number"
              min="0"
              step="0.5"
              placeholder="5"
              required
            >
          </div>

        </div>

        <details>
          <summary>
            Anything AOO should avoid? (optional)
          </summary>

          <div class="exclusions">

            <label class="check">
              <input
                type="checkbox"
                value="competitions"
                data-exclusion
              >
              <span>
                Do not show competitions or hackathons
              </span>
            </label>

            <label class="check">
              <input
                type="checkbox"
                value="grants"
                data-exclusion
              >
              <span>
                Do not show grants or funding calls
              </span>
            </label>

            <label class="check">
              <input
                type="checkbox"
                value="financial_trading"
                data-exclusion
              >
              <span>
                Do not show investing, trading or financial mechanisms
              </span>
            </label>

            <label class="check">
              <input
                type="checkbox"
                value="customer_work"
                data-exclusion
              >
              <span>
                Do not show opportunities that require customer/client work
              </span>
            </label>

            <label class="check">
              <input
                type="checkbox"
                value="selling_content"
                data-exclusion
              >
              <span>
                Do not show opportunities that depend on selling or content
              </span>
            </label>

          </div>
        </details>

        <details>
          <summary>
            Skills or assets AOO can use (optional)
          </summary>

          <div
            class="field"
            style="margin-top:16px"
          >
            <label for="skills">
              Skills / assets
            </label>

            <input
              id="skills"
              placeholder="e.g. Python, domain knowledge, audience, existing code"
            >

            <span class="help">
              Separate items with commas.
            </span>
          </div>
        </details>

        <button
          class="primary"
          type="submit"
          id="findButton"
          aria-label="Find what AI can do for me"
        >
          Find my best opportunities
        </button>

        <div
          class="status"
          id="status"
          aria-live="polite"
        ></div>

        <div class="safety">
          Exploring does not authorize spending,
          trading, registration, applications,
          submissions or identity representation.
        </div>

      </form>
    </section>

    <section
      class="results"
      id="results"
      hidden
    >
      <h2>Your best current leads</h2>

      <div class="results-intro">
        AOO shows at most three.
        Unknown facts stay unknown instead of being guessed.
      </div>

      <div
        class="cards"
        id="cards"
      ></div>

      <div
        class="effects"
        id="effects"
        hidden
      ></div>

      <div
        class="notice"
        id="notices"
      ></div>
    </section>

  </main>

  <footer class="footer">
    AOO can consider software, automation, data products,
    APIs, businesses, grants, competitions, bounties,
    financial/trading mechanisms and other legal
    machine-heavy opportunities.
    <br><br>
    <a href="/judge-console#verified-proof">
      View verified 7-agent proof
    </a>
  </footer>

</div>

<script>
(() => {
  "use strict";

  const q = (id) =>
    document.getElementById(id);

  const COUNTRY_CODES = (
    "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ "
    + "BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ "
    + "CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ "
    + "DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR "
    + "GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY "
    + "HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP "
    + "KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY "
    + "MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ "
    + "NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY "
    + "QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ "
    + "TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ "
    + "VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW XK"
  ).split(" ");

  const displayNames =
    typeof Intl.DisplayNames === "function"
      ? new Intl.DisplayNames(
          ["en"],
          {type: "region"}
        )
      : null;

  function countryName(code) {
    try {
      return displayNames
        ? displayNames.of(code) || code
        : code;
    } catch (_) {
      return code;
    }
  }

  function countryOptions(selected) {
    const values = COUNTRY_CODES
      .map((code) => ({
        code,
        name: countryName(code)
      }))
      .sort((a, b) =>
        a.name.localeCompare(b.name)
      );

    return (
      '<option value="">Choose country</option>'
      + values.map(({code, name}) =>
        '<option value="'
        + escapeHtml(name)
        + '" data-code="'
        + code
        + '"'
        + (code === selected ? " selected" : "")
        + ">"
        + escapeHtml(name)
        + "</option>"
      ).join("")
    );
  }

  function populateResidence() {
    q("residence").innerHTML =
      countryOptions("BG");
  }

  function currencyCodes() {
    let values = [];

    try {
      if (
        typeof Intl.supportedValuesOf
        === "function"
      ) {
        values =
          Intl.supportedValuesOf(
            "currency"
          );
      }
    } catch (_) {
      values = [];
    }

    const fallback = [
      "USD", "EUR", "GBP", "BGN",
      "PHP", "JPY", "CNY", "AUD",
      "CAD", "CHF", "INR", "BRL",
      "MXN", "SGD", "HKD", "AED",
      "TRY", "PLN", "RON", "SEK",
      "NOK", "DKK", "CZK", "HUF",
      "NZD", "ZAR", "KRW", "THB",
      "IDR", "MYR", "VND", "ILS",
      "SAR"
    ];

    values = [
      ...new Set([
        ...values,
        ...fallback,
        "USDC",
        "USDT"
      ])
    ].sort();

    return values;
  }

  function populateCurrencies() {
    q("currency").innerHTML =
      '<option value="">Currency</option>'
      + currencyCodes()
        .map((code) =>
          '<option value="'
          + code
          + '">'
          + code
          + "</option>"
        )
        .join("");
  }

  function addCitizenship(
    selected = "BG"
  ) {
    const select =
      document.createElement(
        "select"
      );

    select.className =
      "citizenship-select";

    select.required = true;

    select.innerHTML =
      countryOptions(selected);

    q("citizenships")
      .appendChild(select);
  }

  function escapeHtml(value) {
    return String(
      value == null ? "" : value
    )
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function metric(label, value) {
    return (
      '<div class="metric">'
      + "<span>"
      + escapeHtml(label)
      + "</span>"
      + "<strong>"
      + escapeHtml(value)
      + "</strong>"
      + "</div>"
    );
  }

  function card(item) {
    const checks =
      Array.isArray(
        item.still_needs_checking
      )
        ? item.still_needs_checking
        : [];

    const source =
      typeof item.source_url === "string"
      && item.source_url.startsWith(
        "https://"
      )
        ? (
            '<a class="action" target="_blank" '
            + 'rel="noopener noreferrer" href="'
            + escapeHtml(
                item.source_url
              )
            + '">View opportunity</a>'
          )
        : "";

    return (
      '<article class="card">'
      + '<div class="card-top">'
      + "<div>"
      + '<div class="category">'
      + escapeHtml(item.category)
      + "</div>"
      + "<h3>"
      + escapeHtml(item.title)
      + "</h3>"
      + "</div>"
      + '<div class="verdict">'
      + "NEEDS CHECKING"
      + "</div>"
      + "</div>"

      + '<div class="why">'
      + "<strong>Why AOO surfaced it for you</strong><br>"
      + escapeHtml(
          item.why_this_fits
        )
      + "</div>"

      + '<div class="metrics">'
      + metric(
          "Potential upside",
          item.potential_upside
        )
      + metric(
          "Money needed",
          item.money_needed
        )
      + metric(
          "Your time needed",
          item.human_time_needed
        )
      + metric(
          "How much AI can do",
          item.ai_share_of_work
        )
      + metric(
          "Eligibility",
          item.eligibility
        )
      + "</div>"

      + '<div class="checking">'
      + "<strong>AOO still needs to check</strong>"
      + "<ul>"
      + checks.map((text) =>
          "<li>"
          + escapeHtml(text)
          + "</li>"
        ).join("")
      + "</ul>"
      + "</div>"

      + '<div class="actions">'
      + source
      + '<a class="action" '
      + 'href="/judge-console#verified-proof">'
      + "See verified AI analysis proof"
      + "</a>"
      + "</div>"
      + "</article>"
    );
  }

  function collectCitizenships() {
    return [
      ...document.querySelectorAll(
        ".citizenship-select"
      )
    ]
      .map((element) =>
        element.value.trim()
      )
      .filter(Boolean);
  }

  function collectExclusions() {
    return [
      ...document.querySelectorAll(
        "[data-exclusion]:checked"
      )
    ].map((element) =>
      element.value
    );
  }

  function collectSkills() {
    return q("skills")
      .value
      .split(",")
      .map((value) =>
        value.trim()
      )
      .filter(Boolean);
  }

  async function submit(event) {
    event.preventDefault();

    const button =
      q("findButton");

    const status =
      q("status");

    const available =
      q("availableMoney")
      .value.trim();

    const maxSpend =
      q("maxSpend")
      .value.trim();

    if (
      Number(maxSpend)
      > Number(available)
    ) {
      status.textContent =
        "Max cash spend/risk cannot be greater than the money available.";
      return;
    }

    const payload = {
      profile_version: "5",
      goal:
        q("goal").value,
      residence_country:
        q("residence").value,
      citizenships:
        collectCitizenships(),
      currency:
        q("currency").value,
      available_money:
        available,
      max_cash_spend_or_risk:
        maxSpend,
      human_hours_per_week:
        q("hours").value.trim(),
      exclusions:
        collectExclusions(),
      skills_assets:
        collectSkills()
    };

    button.disabled = true;
    status.textContent =
      "Checking your limits against the current opportunity evidence…";

    try {
      const response =
        await fetch(
          "/opportunities/personalized",
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json"
            },
            body:
              JSON.stringify(
                payload
              )
          }
        );

      const data =
        await response.json();

      if (
        !response.ok
        || data.status !== "PASS"
      ) {
        throw new Error(
          "AOO could not use this profile. Check the fields and try again."
        );
      }

      const recommendations =
        Array.isArray(
          data.recommendations
        )
          ? data.recommendations
          : [];

      q("cards").innerHTML =
        recommendations.length
          ? recommendations
              .map(card)
              .join("")
          : (
              '<div class="empty">'
              + "<strong>No honest recommendation yet.</strong><br>"
              + escapeHtml(
                  data.empty_reason
                  || "Nothing survives the current evidence and limits."
                )
              + "</div>"
            );

      const effects =
        Array.isArray(
          data.profile_effects
        )
          ? data.profile_effects
          : [];

      if (effects.length) {
        q("effects").hidden =
          false;

        q("effects").innerHTML =
          "<strong>What your profile changed</strong>"
          + "<ul>"
          + effects.map((text) =>
              "<li>"
              + escapeHtml(text)
              + "</li>"
            ).join("")
          + "</ul>";
      } else {
        q("effects").hidden =
          true;
        q("effects").innerHTML =
          "";
      }

      const warnings =
        Array.isArray(
          data.warnings
        )
          ? data.warnings
          : [];

      q("notices").innerHTML =
        "<strong>What AOO refuses to guess</strong><br><br>"
        + warnings
            .map(escapeHtml)
            .join("<br><br>");

      q("results").hidden =
        false;

      status.textContent =
        recommendations.length
          ? (
              "Found "
              + recommendations.length
              + " current lead"
              + (
                  recommendations.length === 1
                    ? "."
                    : "s."
                )
            )
          : "No recommendation passed the current evidence gate.";

      q("results")
        .scrollIntoView({
          behavior: "smooth",
          block: "start"
        });

    } catch (error) {
      status.textContent =
        String(
          error.message
          || error
        );
    } finally {
      button.disabled = false;
    }
  }

  populateResidence();
  populateCurrencies();
  addCitizenship("BG");

  q("addCitizenship")
    .addEventListener(
      "click",
      () =>
        addCitizenship("")
    );

  q("profileForm")
    .addEventListener(
      "submit",
      submit
    );
})();
</script>

</body>
</html>
'''


__all__ = [
    "render_public_v5_home",
]

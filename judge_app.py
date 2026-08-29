from __future__ import annotations

import inspect
from typing import Any, Callable

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response

import main as production
from fastapi.responses import HTMLResponse
from opportunity_operator.public_v5_home import render_public_v5_home
from opportunity_operator.public_v5_operator import build_public_v5_view


PUBLIC_JUDGE_MODE = True

BLOCKED_MUTATION_PATHS = {
    "/discover/refresh",
    "/opportunities/synthesize",
    "/proof/discovered",
    "/proof/human-gate",
    "/intake/primary-source",
    "/decision/primary-source",
}

LOCK_REASON = (
    "This public judge service is intentionally model-free and "
    "cost-safe. Live Google ADK + Gemini execution is demonstrated "
    "in the contest proof-of-action video and preserved in the "
    "private production service."
)


def _production_endpoint(
    path: str,
    method: str,
) -> Callable[..., Any]:
    wanted = method.upper()

    for route in production.app.routes:
        if getattr(route, "path", None) != path:
            continue

        methods = {
            str(value).upper()
            for value in (
                getattr(route, "methods", None)
                or set()
            )
        }

        if wanted in methods:
            return route.endpoint

    raise RuntimeError(
        f"required production route missing: "
        f"{wanted} {path}"
    )


async def _invoke(
    endpoint: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    value = endpoint(*args, **kwargs)

    if inspect.isawaitable(value):
        value = await value

    return value


def _html_text(
    response: Any,
) -> str:
    if isinstance(response, Response):
        return response.body.decode(
            response.charset or "utf-8"
        )

    return str(response)


PUBLIC_MODE_STYLE = r"""
<style id="aoo-public-judge-mode-style">

.aoo-public-guide {
  width: min(1440px, calc(100% - 40px));
  margin: 14px auto 0;
  padding: 15px 17px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border: 1px solid rgba(110,231,183,.22);
  border-radius: 14px;
  color: #d6f3e7;
  background:
    linear-gradient(
      135deg,
      rgba(110,231,183,.07),
      rgba(141,174,255,.045)
    );
  font-family:
    Inter,
    ui-sans-serif,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
  font-size: 11px;
  line-height: 1.5;
}

.aoo-public-guide-copy {
  min-width: 0;
}

.aoo-public-kicker {
  display: block;
  margin-bottom: 3px;
  color: #8daeff;
  text-transform: uppercase;
  letter-spacing: .12em;
  font-size: 9px;
  font-weight: 850;
}

.aoo-public-guide strong {
  display: block;
  color: #f4fff9;
  font-size: 14px;
}

.aoo-public-guide span:last-child {
  display: block;
  margin-top: 3px;
  color: #b8c5d8;
}

.aoo-public-guide-actions {
  flex: 0 0 auto;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.aoo-public-guide a,
.aoo-public-proof-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 12px;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 760;
}

.aoo-public-guide a:first-child {
  color: #08101f;
  background:
    linear-gradient(
      90deg,
      #91b0ff,
      #c0acff
    );
}

.aoo-public-guide a:last-child {
  color: #d6ddec;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.035);
}

.aoo-public-readonly-note {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(141,174,255,.18);
  border-radius: 11px;
  color: #c7d3ee;
  background: rgba(141,174,255,.045);
  font-size: 11px;
  line-height: 1.55;
}

.aoo-public-readonly-note strong {
  color: #f3f6ff;
}

@media (max-width: 760px) {
  .aoo-public-guide {
    align-items: flex-start;
    flex-direction: column;
  }
}

</style>
"""

PUBLIC_MODE_BANNER = r"""
<div
  class="aoo-public-guide"
  id="aooPublicProductGuide"
  role="note"
>
  <div class="aoo-public-guide-copy">
    <span class="aoo-public-kicker">
      Public judge demo · Start here
    </span>

    <strong>
      This is the Autonomous Opportunity Operator.
    </strong>

    <span>
      1 · Set your goal, resources and limits.
      2 · Click “Find what AI can do for me”.
      3 · Review your personalized Decision Inbox.
      No sign-up or model spend is required.
    </span>
  </div>

  <div class="aoo-public-guide-actions">
    <a href="#frontdoor">
      Start with my profile ↓
    </a>

    <a href="/judge-console">
      Technical proof
    </a>
  </div>
</div>
"""

PUBLIC_CONSOLE_BANNER = r"""
<div
  class="aoo-public-guide"
  id="aooPublicConsoleGuide"
  role="note"
>
  <div class="aoo-public-guide-copy">
    <span class="aoo-public-kicker">
      Public judge demo · Read-only technical proof
    </span>

    <strong>
      Technical proof — not the product interface.
    </strong>

    <span>
      This page shows the verified seven-agent architecture,
      deterministic tools, provenance, replay and reference-run
      evidence. Live Gemini execution is intentionally unavailable
      to anonymous visitors.
    </span>
  </div>

  <div class="aoo-public-guide-actions">
    <a href="/">
      ← Open AOO product
    </a>

    <a href="#verified-proof">
      View verified run
    </a>
  </div>
</div>
"""

PUBLIC_MODE_SCRIPT = r"""
<script id="aoo-public-judge-mode-script">
(() => {
  "use strict";

  const blocked = new Set([
    "/discover/refresh",
    "/opportunities/synthesize",
    "/proof/discovered",
    "/proof/human-gate",
    "/intake/primary-source",
    "/decision/primary-source"
  ]);

  const isConsole =
    window.location.pathname === "/judge-console";

  const originalFetch =
    window.fetch.bind(window);

  window.fetch = function(input, init) {
    let pathname = "";

    try {
      pathname = new URL(
        typeof input === "string"
          ? input
          : input.url,
        window.location.href
      ).pathname;
    } catch (_) {
      pathname = "";
    }

    const method = String(
      (init && init.method)
      || (
        typeof input !== "string"
        && input.method
      )
      || "GET"
    ).toUpperCase();

    if (
      method !== "GET"
      && method !== "HEAD"
      && blocked.has(pathname)
    ) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "JUDGE_DEMO_LOCKED",
            reason_codes: [
              "ANONYMOUS_COST_BEARING_ACTION_DISABLED"
            ]
          }),
          {
            status: 403,
            headers: {
              "Content-Type": "application/json"
            }
          }
        )
      );
    }

    return originalFetch(input, init);
  };


  function replaceInvestigateButtons() {

    if (isConsole) {
      return;
    }

    document
      .querySelectorAll("[data-investigate]")
      .forEach((button) => {

        const link =
          document.createElement("a");

        link.className =
          button.className
          || "button primary";

        link.href =
          "/judge-console#verified-proof";

        link.textContent =
          "View verified 7-agent proof";

        link.title =
          "Open the read-only technical proof "
          + "for the verified seven-agent workflow.";

        link.setAttribute(
          "data-public-proof-link",
          "1"
        );

        button.replaceWith(link);
      });
  }


  function lockProductOnlyControls() {

    if (isConsole) {
      return;
    }

    const refresh =
      document.getElementById(
        "refreshButton"
      );

    if (refresh) {
      refresh.disabled = true;
      refresh.textContent =
        "Fresh discovery shown in demo video";
      refresh.title =
        "Fresh network discovery is disabled "
        + "on the anonymous judge service.";
    }

    replaceInvestigateButtons();
  }


  function makeConsoleReadOnly() {

    if (!isConsole) {
      return;
    }

    const preflight =
      document.getElementById(
        "preflightButton"
      );

    const live =
      document.getElementById(
        "liveButton"
      );

    let actions = null;

    if (preflight) {
      preflight.disabled = true;
      preflight.hidden = true;
      preflight.setAttribute(
        "aria-hidden",
        "true"
      );
      actions = preflight.closest(
        ".actions"
      );
    }

    if (live) {
      live.disabled = true;
      live.hidden = true;
      live.setAttribute(
        "aria-hidden",
        "true"
      );

      if (!actions) {
        actions = live.closest(
          ".actions"
        );
      }
    }

    if (
      actions
      && !actions.querySelector(
        "[data-public-readonly-note]"
      )
    ) {
      const note =
        document.createElement("div");

      note.className =
        "aoo-public-readonly-note";

      note.setAttribute(
        "data-public-readonly-note",
        "1"
      );

      note.innerHTML =
        "<strong>Read-only public proof.</strong> "
        + "The buttons that start source ingestion "
        + "or Gemini execution are intentionally removed "
        + "from this anonymous service. "
        + "Use this page to inspect the verified run, "
        + "agents, tools, provenance and safety boundary.";

      actions.appendChild(note);
    }

    const placeholder =
      document.querySelector(
        ".placeholder-intro"
      );

    if (placeholder) {
      placeholder.innerHTML =
        "<strong>Verified workflow evidence</strong>"
        + "This public page does not start a new workflow. "
        + "The contest proof-of-action video demonstrates "
        + "the live Google ADK + Gemini execution.";
    }

    const proof =
      document.querySelector(
        ".hero-proof"
      );

    if (
      proof
      && !proof.id
    ) {
      proof.id = "verified-proof";
    }
  }


  function enforcePublicUx() {
    lockProductOnlyControls();
    makeConsoleReadOnly();
  }


  enforcePublicUx();

  /*
   * Public product cards are re-rendered after personalization.
   * Observe only that bounded container and only re-apply the
   * investigate-button replacement there.
   *
   * Do NOT observe document.documentElement: enforcePublicUx()
   * itself changes DOM text/children, which can create a
   * self-triggering MutationObserver loop.
   */
  if (!isConsole) {
    const lanes =
      document.getElementById(
        "productLanes"
      );

    if (lanes) {
      const lanesObserver =
        new MutationObserver(
          () => {
            replaceInvestigateButtons();
          }
        );

      lanesObserver.observe(
        lanes,
        {
          childList: true,
          subtree: true
        }
      );
    }
  }
})();
</script>
"""


def _inject_public_mode(
    html: str,
) -> str:

    is_console = (
        'id="preflightButton"' in html
        and
        'id="liveButton"' in html
    )

    banner = (
        PUBLIC_CONSOLE_BANNER
        if is_console
        else PUBLIC_MODE_BANNER
    )

    if is_console:

        html = html.replace(
            'id="preflightButton"',
            (
                'id="preflightButton" '
                'disabled hidden '
                'aria-hidden="true"'
            ),
            1,
        )

        html = html.replace(
            'id="liveButton"',
            (
                'id="liveButton" '
                'disabled hidden '
                'aria-hidden="true"'
            ),
            1,
        )

        html = html.replace(
            '<div class="hero-proof">',
            (
                '<div '
                'class="hero-proof" '
                'id="verified-proof">'
            ),
            1,
        )

    if "<body" in html:

        body_index = html.find(
            "<body"
        )

        if body_index >= 0:

            body_close = html.find(
                ">",
                body_index,
            )

            if body_close >= 0:

                html = (
                    html[: body_close + 1]
                    + PUBLIC_MODE_STYLE
                    + banner
                    + html[body_close + 1 :]
                )

    if "</body>" in html:

        html = html.replace(
            "</body>",
            PUBLIC_MODE_SCRIPT
            + "\n</body>",
            1,
        )

    else:

        html += PUBLIC_MODE_SCRIPT

    return html


_prod_home = _production_endpoint("/", "GET")
_prod_judge = _production_endpoint(
    "/judge-console",
    "GET",
)
_prod_health = _production_endpoint(
    "/health",
    "GET",
)
_prod_provenance = _production_endpoint(
    "/provenance",
    "GET",
)
_prod_opportunities = _production_endpoint(
    "/opportunities",
    "GET",
)
_prod_personalized = _production_endpoint(
    "/opportunities/personalized",
    "POST",
)


app = FastAPI(
    title="AOO Public Judge Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get(
    "/",
    response_class=HTMLResponse,
)
async def product_home() -> HTMLResponse:
    # AOO_V5_PUBLIC_ROOT
    return HTMLResponse(render_public_v5_home())
    original = await _invoke(
        _prod_home
    )

    return HTMLResponse(
        content=_inject_public_mode(
            _html_text(original)
        )
    )


@app.get(
    "/judge-console",
    response_class=HTMLResponse,
)
async def judge_console() -> HTMLResponse:
    original = await _invoke(
        _prod_judge
    )

    return HTMLResponse(
        content=_inject_public_mode(
            _html_text(original)
        )
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    original = await _invoke(
        _prod_health
    )

    if not isinstance(original, dict):
        original = {
            "status": "ok",
        }

    return {
        **original,
        "public_judge_mode": True,
        "anonymous_model_execution": False,
    }


@app.get("/provenance")
async def provenance() -> dict[str, Any]:
    original = await _invoke(
        _prod_provenance
    )

    if not isinstance(original, dict):
        original = {}

    return {
        **original,
        "public_judge_mode": True,
        "anonymous_cost_bearing_routes":
            "LOCKED",
    }


@app.get("/opportunities")
async def opportunities() -> Any:
    return await _invoke(
        _prod_opportunities
    )


@app.post("/opportunities/personalized")
async def personalized(
    payload: dict[str, Any],
) -> Any:
    # AOO_V5_PUBLIC_PERSONALIZATION
    if isinstance(payload, dict) and payload.get("profile_version") == "5":
        return build_public_v5_view(payload)
    return await _invoke(
        _prod_personalized,
        payload,
    )


@app.api_route(
    "/{path:path}",
    methods=[
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ],
)
async def block_anonymous_mutation(
    path: str,
) -> JSONResponse:
    normalized = "/" + path.lstrip("/")

    return JSONResponse(
        status_code=403,
        content={
            "status":
                "JUDGE_DEMO_LOCKED",
            "requested_path":
                normalized,
            "reason_codes": [
                "ANONYMOUS_COST_BEARING_ACTION_DISABLED",
            ],
            "detail":
                LOCK_REASON,
        },
    )

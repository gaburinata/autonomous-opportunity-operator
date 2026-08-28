from __future__ import annotations

import inspect
from typing import Any, Callable

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response

import main as production


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
.aoo-public-judge-mode {
  width: min(1440px, calc(100% - 40px));
  margin: 14px auto 0;
  padding: 11px 14px;
  border: 1px solid rgba(110,231,183,.22);
  border-radius: 12px;
  color: #d6f3e7;
  background: rgba(110,231,183,.055);
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
.aoo-public-judge-mode strong {
  color: #f4fff9;
}
</style>
"""

PUBLIC_MODE_BANNER = r"""
<div class="aoo-public-judge-mode" role="note">
  <strong>Public judge demo · cost-safe mode.</strong>
  Product exploration, deterministic personalization,
  provenance and technical proof remain available here.
  Fresh discovery and live Google ADK + Gemini execution
  are deliberately locked on the anonymous service.
  The unedited contest demo shows the verified live workflow.
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

  const originalFetch = window.fetch.bind(window);

  window.fetch = function(input, init) {
    let pathname = "";

    try {
      pathname = new URL(
        typeof input === "string" ? input : input.url,
        window.location.href
      ).pathname;
    } catch (_) {
      pathname = "";
    }

    const method = String(
      (init && init.method)
      || (typeof input !== "string" && input.method)
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

  function lockExpensiveControls() {
    const refresh = document.getElementById(
      "refreshButton"
    );

    if (refresh) {
      refresh.disabled = true;
      refresh.textContent =
        "Live discovery shown in demo video";
      refresh.title =
        "Disabled on the anonymous judge service.";
    }

    document
      .querySelectorAll("[data-investigate]")
      .forEach((button) => {
        button.disabled = true;
        button.textContent =
          "7-agent run shown in demo video";
        button.title =
          "Live Gemini execution is locked "
          + "on the anonymous judge service.";
      });

    document
      .querySelectorAll("button")
      .forEach((button) => {
        const text = String(
          button.textContent || ""
        ).toLowerCase();

        const expensive =
          text.includes("live workflow")
          || text.includes("fresh workflow")
          || (
            text.includes("gemini")
            && (
              text.includes("run")
              || text.includes("start")
            )
          );

        if (expensive) {
          button.disabled = true;
          button.title =
            "Live model execution is demonstrated "
            + "in the contest video.";
        }
      });
  }

  lockExpensiveControls();

  const observer = new MutationObserver(
    lockExpensiveControls
  );

  observer.observe(
    document.documentElement,
    {
      childList: true,
      subtree: true
    }
  );

  document.addEventListener(
    "click",
    (event) => {
      const button =
        event.target.closest("button");

      if (!button || !button.disabled) {
        return;
      }

      event.preventDefault();
      event.stopImmediatePropagation();
    },
    true
  );
})();
</script>
"""


def _inject_public_mode(
    html: str,
) -> str:
    if "<body" in html:
        start = html.find(">")
        body_index = html.find("<body")

        if body_index >= 0:
            body_close = html.find(
                ">",
                body_index,
            )

            if body_close >= 0:
                html = (
                    html[: body_close + 1]
                    + PUBLIC_MODE_STYLE
                    + PUBLIC_MODE_BANNER
                    + html[body_close + 1 :]
                )

    if "</body>" in html:
        html = html.replace(
            "</body>",
            PUBLIC_MODE_SCRIPT + "\n</body>",
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

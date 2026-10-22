# garment_ai_intelligence — Implementation Notes

Module 25 of the Smart Complete Garment Software suite: **AI Intelligence &
Decision Support Platform**. Source: `AI Intelligence Platform .txt` (SRS
Parts 1-3, sections 1-59).

The SRS describes a very large surface — full ML/NLP/computer-vision/GenAI
chatbot platform across every ERP domain (production forecasting, quality
CV inspection, HR analytics, finance fraud detection, WhatsApp/Teams
chatbots...). Several of those predictive features **already exist** as
deterministic heuristic scorers bolted onto the shared abstract
`garment.ai.engine` (originally defined in `garment_buyer_crm`) inside their
own domain modules — see the "What already exists elsewhere" table below.
Re-building them here would duplicate real, working code. Instead this
module is realistically scoped to what the SRS is actually missing: a
**governed config/log layer** for that whole cross-module AI pattern, plus
**one genuinely computed end-to-end feature** (Demand Forecasting) that did
not exist anywhere yet.

## New models (7)

| Model | Purpose |
|---|---|
| `garment.ai.provider.config` | External AI provider settings — OpenAI / Anthropic / Azure OpenAI / Custom endpoint, API key (password widget, `groups=`-restricted to the AI Administrator group at the FIELD level, not just the view), model name, enabled flag, `is_default` fallback. |
| `garment.ai.provider.feature.line` | Per-feature routing child table on the config above — e.g. route `demand_forecast` calls to a cheap model, `quality_prediction` to a stronger one. |
| `garment.ai.prompt.template` | Reusable, versioned prompt library keyed by use-case, with a `render(**kwargs)` placeholder-fill helper, so external LLM calls are built from a governed template instead of an inline string in Python. |
| `garment.ai.insight` | The UNIFIED cross-module insight/prediction log — `insight_type` (demand-forecast / risk-alert / anomaly / recommendation / similarity-match), generic `res_model`/`res_id` back-reference to the source record, `confidence`, `status` (new/reviewed/actioned/dismissed) review workflow, free-text `explanation`. |
| `garment.demand.forecast` (+ `.line`) | THE real, working feature — see below. |
| `garment.ai.usage.log` | API call audit trail — tokens in/out, estimated cost, latency, success/error, for cost governance. |

Plus one **in-place extension**: `garment.ai.engine` (abstract, defined in
`garment_buyer_crm`) gains `call_llm(feature_code, prompt, res_model=False,
res_id=False, prompt_template_id=False)` in `models/garment_ai_engine.py` —
a generic external-LLM call routed through this module's
`garment.ai.provider.config` instead of the base engine's plain
`ir.config_parameter` reads, guarded by `try/except`, and always logging one
`garment.ai.usage.log` row (success or failure).

## The one real, working, end-to-end feature: AI Demand Forecasting (SRS §25)

`GarmentDemandForecast.action_generate_demand_forecast()`:

1. Queries real `garment.order.line` records for the selected `style_id`
   (optionally narrowed to `buyer_id`, via the line's own stored related
   field) — **not** a mock/random dataset.
2. Groups historical quantity by calendar month (or quarter) of the parent
   `garment.order.order_date`.
3. Applies one of three genuinely computed methods over the configured
   historical-basis window (last 3/6/12 periods, or all history):
   - **Simple Moving Average** — plain mean of the recent periods.
   - **Recency-Weighted Trend** — linearly increasing weights (1, 2, 3...)
     so more recent periods count more.
   - **Simple Average (All History)** — mean across every period on record.
4. Computes a deterministic confidence score from (a) how many historical
   periods were available and (b) their period-to-period coefficient of
   variation — more data + lower variance = higher confidence, capped
   10-85%. Zero historical data → 0 forecast, 10% confidence, and an
   explicit explanation saying so (never a fabricated number).
5. Writes a full period breakdown (`garment.demand.forecast.line`:
   historical periods actually used + the projected future periods) and a
   plain-English `explanation` describing exactly what was used and how.
6. Logs one `garment.ai.insight` (`insight_type='demand_forecast'`,
   `source='heuristic'`) pointing back at the forecast record, and links it
   via `basis_order_ids` (a real `garment.order` Many2many) so a user can
   click straight through to the historical orders that produced the
   number.

This can be verified end-to-end with zero configuration and zero external
API key — exactly the "realistically scoped, no fake black box" brief.

## External LLM integration — untested but implemented

`GarmentAIEngineIntelligencePlatformExtension.call_llm()`
(`models/garment_ai_engine.py`) implements a real `requests.post()` call to
OpenAI-compatible chat-completions (OpenAI/Azure/Custom) and Anthropic's
Messages API, with real per-provider header/payload construction and real
response parsing (including token usage extraction for the cost log). It is
wrapped in a broad `try/except Exception` so a network failure, bad API key,
or malformed response is caught, logged (`_logger.warning` + a
`garment.ai.usage.log` row with `status='error'`), and returned as
`{'success': False, 'error': ...}` — it never raises into a calling business
flow.

**Honesty about test status**: there is no real OpenAI/Anthropic/Azure API
key available in this sandbox, so this code path has **never been exercised
against a live endpoint** — only `python3 -m py_compile`d. The demonstrated,
verified feature is the deterministic demand forecast above, which needs no
external call at all (same "always works out of the box" philosophy already
used by `garment.ai.engine.score_buyer()`'s fallback scorer in
`garment_buyer_crm`, and by every sibling module's own AI extension —
`predict_order_risk`, `run_breakdown_risk_prediction`, etc.). No module in
this suite currently calls `call_llm()` — it is offered as the shared entry
point for the next module that wants to make a real external call (see
Follow-ups below).

## What already exists elsewhere (NOT duplicated here)

Per the SRS's very broad AI surface, the following are **already real,
working models in sibling modules** and were deliberately left alone:

| SRS Section | Already implemented as | Module |
|---|---|---|
| §13-16 Production/capacity/delay/line-balancing prediction | `predict_order_risk` / `predict_order_delivery` / `optimize_order_allocation` (garment.ai.engine extension) | garment_order_management |
| §21-24 Quality risk prediction / defect classification | `garment.quality.ai.analysis` | garment_quality |
| §29-30 Procurement intelligence / supplier ranking | `garment.supplier.rating`, `garment.supplier.risk` | garment_supplier |
| §33-36 HR analytics / workforce planning | `garment.ie.ai.insight`, `garment.hr.performance` | garment_ie_management, garment_hr |
| Breakdown / spare-parts forecasting | `garment.maintenance.ai.prediction` | garment_maintenance |
| Lead scoring | `garment.ai.engine.score_buyer()` (base engine) | garment_buyer_crm |

This module does not re-model any of these. Its job is the config/log layer
underneath them all, plus the one net-new capability (demand forecasting)
that had no home yet.

## Deliberately simplified / out of scope

- **Computer Vision defect detection (§22-24)** — camera hardware / image
  model integration is out of scope for an Odoo Community addon; not
  modeled at all (no fabricated "detected defect" data).
- **AI ERP Chatbot / NLQ / multi-channel chat (§6-10, 48-49)** — no chat UI,
  no WhatsApp/Teams/Telegram integration. `garment.ai.prompt.template` seeds
  a `chatbot` use-case template as the governance starting point such a
  feature would build on, but no chat surface is built.
- **AI Executive Dashboard (§11, 53)** — Odoo Community has no dashboard
  app; delivered instead as the `garment.ai.usage.log` pivot view (cost/
  token analytics) and standard tree/search views, consistent with the
  "act_window views, not a bespoke dashboard" pattern already used by
  sibling modules (e.g. garment_maintenance's KPI views).
- **Cost optimization / garment cost prediction (§27-28)**, **finance
  intelligence / cash flow / fraud detection (§37-39)**, **inventory
  optimization / stockout prevention (§31-32)** — no new dedicated models;
  these either already have a real home (`garment.costing`,
  `garment.purchase.forecast`) or are legitimately out of scope for this
  module. Any future heuristic for them can log through the now-existing
  `garment.ai.insight` unified table with `insight_type='recommendation'`
  or `'anomaly'` without a schema change.
- **Generative AI report/email/meeting assistants (§41-47)** — no bespoke
  report generator, email drafter or meeting-transcription feature is
  built. The governed building blocks (`garment.ai.prompt.template` +
  `garment.ai.engine.call_llm()`) are implemented so a future module can
  build these without re-inventing prompt governance or usage logging.
- **AI Training Data Management (§51)** — no real ML model training happens
  in this sandbox (explicitly out of scope per the task brief); every
  "prediction" in this suite is a deterministic, auditable heuristic.
- **Bespoke REST API layer (§54)** — standard Odoo XML-RPC/JSON-RPC already
  exposes every model in this module; no custom `/api/ai/*` controller
  was added.
- **AI Model Management / Monitoring (§50, 52)** is covered structurally by
  `garment.ai.provider.config` (which "model" is active/enabled) and
  `garment.ai.usage.log` (accuracy/latency/error-rate style monitoring is
  approximated by success/error status + latency_ms — true prediction
  accuracy tracking would require ground-truth outcome data this sandbox
  does not have).
- `estimate_cost()` on `garment.ai.provider.config` uses a single flat
  placeholder USD/1K-token rate (documented in the code) — a real
  deployment would look this up per model/provider.

## Follow-up (not done in this module, per task instructions)

`garment.ai.insight` is designed to be the natural consolidation point for
the several scattered `garment.xxx.ai.*` log models sibling modules already
built independently (`garment.quality.ai.analysis`,
`garment.maintenance.ai.prediction`, `garment.ie.ai.insight`, and the
non-persisted risk fields on `garment.order`/`garment.order.risk`). Migrating
those to write into (or additionally write into) `garment.ai.insight` is a
real, non-trivial cross-module change — each has its own workflow/views/
security wired to its own model — and is intentionally **not** attempted
here. A future migration would, per model: add a `garment.ai.insight`
creation call alongside (not replacing) the existing local record on each
predictor method, using `res_model`/`res_id` to point back at the local
record so nothing already built breaks.

Similarly, no sibling module's `garment.ai.engine` extension was modified to
call this module's new `call_llm()` — doing so is future work once a real
provider API key exists to validate against.

## Cross-module links

- `garment.demand.forecast.style_id` → `garment.style` (garment_style_library, reused, not duplicated).
- `garment.demand.forecast.buyer_id` → `garment.buyer` (garment_buyer_crm, reused).
- `garment.demand.forecast` historical basis queries `garment.order.line` / `garment.order` (garment_order_management) directly — real data, not a copy.
- `garment.ai.engine` is inherited (`_inherit`), not redefined — same abstract model already extended by garment_order_management, garment_quality, garment_maintenance, garment_compliance, garment_plm, garment_ie_management.

## Security

Three roles (`module_category_garment_ai_intelligence`): **AI Business
User** (view insights/forecasts), **AI Analyst** (generate forecasts,
review/action insights, implies User), **AI Administrator** (provider
config, prompt templates, full access, implies Analyst). The API key field
additionally carries a field-level `groups=` restriction to AI Administrator
— even a user with model-level read access to `garment.ai.provider.config`
cannot read `api_key` unless they hold that group.

## Validation

- `python3 -m py_compile` — all 8 `.py` files pass.
- `xmllint --noout` — all 9 `.xml` files pass.
- Every model has `ir.model.access.csv` rows (7 models × up to 3 rows); every
  CSV `model_id:id` was checked against the real `model_<name_with_underscores>`
  generated from each model's `_name`.
- Every `res.groups` referenced from a view/field (`groups="..."`) exists in
  `security/garment_ai_intelligence_security.xml`.
- Every `ir.actions.act_window` referenced from the menu file is defined in
  a views file loaded earlier in the manifest; no orphan actions were left
  in views (the initially-drafted standalone action for
  `garment.ai.provider.feature.line` was removed once its coverage via the
  provider config's inline "Feature Routing" tab was confirmed sufficient).
  `manifest['data']` load order is security → data → views → menus (last).
- No `attrs=`/`states=` view syntax used anywhere (direct `invisible=`/
  `readonly=`/`required=` attribute expressions throughout, per house
  style).

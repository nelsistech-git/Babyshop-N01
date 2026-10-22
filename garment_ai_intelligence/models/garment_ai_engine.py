# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends the shared abstract ``garment.ai.engine`` (garment_buyer_crm) with a
generic external-LLM call routed through THIS module's config layer
(``garment.ai.provider.config`` / ``garment.ai.provider.feature.line``)
instead of the base engine's plain ``ir.config_parameter`` reads. This is
the "proper home" referenced in the module description.

IMPORTANT — sandbox limitation: there is no real provider API key configured
in this environment, so ``call_llm`` below has never been exercised against
a live OpenAI/Anthropic/Azure endpoint. It IS implemented for real (real
``requests.post`` call, real payload shape per provider, real response
parsing) behind a guarded ``try/except`` that never lets an external-AI
failure break a calling business flow — see IMPLEMENTATION_NOTES.md,
"Untested but implemented", for the honest status of this code path.
"""
import logging
import time

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover - requests ships with Odoo, kept defensive
    requests = None


class GarmentAIEngineIntelligencePlatformExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    def call_llm(self, feature_code, prompt, res_model=False, res_id=False, prompt_template_id=False):
        """Generic pluggable external-LLM call for a given feature, routed
        through ``garment.ai.provider.config``. Always returns a dict and
        NEVER raises — a missing/disabled provider or a network/API failure
        is reported back as ``{'success': False, 'error': ...}`` so callers
        can fall back to their own deterministic heuristic, exactly like
        ``garment.demand.forecast`` does today without calling this at all.

        Every attempt — success or failure — writes one
        ``garment.ai.usage.log`` row for cost governance.
        """
        Config = self.env['garment.ai.provider.config']
        config = Config.sudo().get_config_for_feature(feature_code)
        UsageLog = self.env['garment.ai.usage.log'].sudo()

        if not config:
            return {'success': False, 'text': '', 'error': 'No enabled AI provider configured for feature "%s".'
                    % feature_code}
        if requests is None:  # pragma: no cover - defensive only
            UsageLog.create(self._usage_vals(config, feature_code, res_model, res_id, prompt_template_id,
                                              status='error', latency_ms=0.0,
                                              error_message='python "requests" library is not available.'))
            return {'success': False, 'text': '', 'error': 'python "requests" library is not available.'}
        if not config.api_key:
            UsageLog.create(self._usage_vals(config, feature_code, res_model, res_id, prompt_template_id,
                                              status='error', latency_ms=0.0,
                                              error_message='Provider configuration has no API key set.'))
            return {'success': False, 'text': '', 'error': 'Provider "%s" has no API key configured.' % config.name}

        started = time.monotonic()
        try:
            headers = {'Content-Type': 'application/json'}
            endpoint = config.effective_endpoint()
            model = config.effective_model()
            if not endpoint:
                raise ValueError('No API endpoint configured for provider "%s".' % config.provider)

            if config.provider == 'anthropic':
                headers['x-api-key'] = config.api_key
                headers['anthropic-version'] = '2023-06-01'
                payload = {'model': model, 'max_tokens': 600, 'messages': [{'role': 'user', 'content': prompt}]}
            else:  # openai / azure_openai / custom - OpenAI-compatible chat completions contract
                headers['Authorization'] = 'Bearer %s' % config.api_key
                payload = {'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.2}

            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if config.provider == 'anthropic':
                text = ''.join(block.get('text', '') for block in data.get('content', [])
                                if block.get('type') == 'text')
                usage = data.get('usage', {})
                tokens_in, tokens_out = usage.get('input_tokens', 0), usage.get('output_tokens', 0)
            else:
                text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                usage = data.get('usage', {})
                tokens_in, tokens_out = usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)

            latency_ms = (time.monotonic() - started) * 1000.0
            UsageLog.create(self._usage_vals(
                config, feature_code, res_model, res_id, prompt_template_id, status='success',
                latency_ms=latency_ms, tokens_input=tokens_in, tokens_output=tokens_out,
                estimated_cost=config.estimate_cost(tokens_in, tokens_out)))
            return {'success': True, 'text': text, 'error': False}

        except Exception as exc:  # noqa: BLE001 - never let an external AI failure break ERP flow
            _logger.warning('garment.ai.engine.call_llm: external call failed for feature "%s" (%s)',
                             feature_code, exc)
            latency_ms = (time.monotonic() - started) * 1000.0
            UsageLog.create(self._usage_vals(config, feature_code, res_model, res_id, prompt_template_id,
                                              status='error', latency_ms=latency_ms, error_message=str(exc)[:2000]))
            return {'success': False, 'text': '', 'error': str(exc)}

    @staticmethod
    def _usage_vals(config, feature_code, res_model, res_id, prompt_template_id, status, latency_ms,
                     tokens_input=0, tokens_output=0, estimated_cost=0.0, error_message=False):
        return {
            'provider_config_id': config.id,
            'prompt_template_id': prompt_template_id or False,
            'feature': feature_code,
            'res_model': res_model or False,
            'res_id': res_id or False,
            'status': status,
            'latency_ms': latency_ms,
            'tokens_input': tokens_input,
            'tokens_output': tokens_output,
            'estimated_cost': estimated_cost,
            'error_message': error_message,
        }

import logging

import requests

_logger = logging.getLogger(__name__)


def reverse_geocode(env, lat, lon):
    """Best effort address lookup through the Google Geocoding API (3 s timeout).
    Returns '' when no key is configured or the call fails - never raises."""
    key = env['ir.config_parameter'].sudo().get_param('nelsis.google_maps_key')
    if not key:
        return ''
    try:
        r = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={'latlng': '%s,%s' % (lat, lon), 'key': key}, timeout=3)
        data = r.json()
        if data.get('status') == 'OK' and data.get('results'):
            return data['results'][0].get('formatted_address', '')[:250]
    except Exception as e:  # noqa: BLE001
        _logger.info('Reverse geocode failed: %s', e)
    return ''

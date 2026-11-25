# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LoginThemeConfig(models.Model):
    """Singleton configuration record that drives the custom login page.

    Only one record is ever meant to exist. `get_config()` is the single
    entry point used both by the QWeb login template and by the media
    controller: it transparently creates the record on first use, so the
    module never breaks even if the default data record was somehow removed.
    """
    _name = 'login.theme.config'
    _description = 'Login Page Theme Configuration'

    name = fields.Char(
        string='Configuration Name',
        default='Default Login Theme',
        required=True,
    )

    # -- Branding -----------------------------------------------------
    company_logo = fields.Binary(
        string='Company Logo',
        attachment=True,
        help='Shown above the login form.',
    )
    company_logo_filename = fields.Char(string='Company Logo Filename')

    welcome_title = fields.Char(
        string='Welcome Title',
        translate=True,
        default='Welcome Back',
    )
    welcome_subtitle = fields.Char(
        string='Welcome Subtitle',
        translate=True,
        default='Enter your credentials to get in',
    )

    # -- Side panel media (image / GIF / video) ------------------------
    media_type = fields.Selection(
        selection=[('image', 'Image / GIF'), ('video', 'Video')],
        string='Side Panel Media Type',
        default='image',
        required=True,
    )
    media_image = fields.Binary(
        string='Side Panel Image / GIF',
        attachment=True,
        help='Displayed beside the login form when Media Type is Image / GIF. '
             'Animated GIFs are supported and will autoplay.',
    )
    media_image_filename = fields.Char(string='Side Panel Image Filename')

    media_video = fields.Binary(
        string='Side Panel Video',
        attachment=True,
        help='MP4 or WEBM file, displayed beside the login form when Media '
             'Type is Video. The video autoplays muted and loops.',
    )
    media_video_filename = fields.Char(string='Side Panel Video Filename')

    media_caption = fields.Char(
        string='Side Panel Caption',
        translate=True,
        help='Optional short tagline overlaid on the side panel.',
    )

    # -- Background (always a static, blurred image) -------------------
    background_image = fields.Binary(
        string='Background Image (glassy blur)',
        attachment=True,
        help='Static image used for the blurred glassy background behind '
             'the login card. If left empty, the Side Panel Image is used '
             'instead (the background is always a static image, even when '
             'the side panel media is a video).',
    )
    background_image_filename = fields.Char(string='Background Image Filename')

    # -- Footer ---------------------------------------------------------
    copyright_text = fields.Char(
        string='Copyright Text',
        translate=True,
    )
    powered_by_text = fields.Char(
        string='Powered By Text',
        translate=True,
    )
    powered_by_image = fields.Binary(
        string='Powered By Image/Logo',
        attachment=True,
    )
    powered_by_image_filename = fields.Char(string='Powered By Image Filename')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if 'copyright_text' in fields_list and not vals.get('copyright_text'):
            year = fields.Date.context_today(self).year
            company_name = self.env.company.name or 'Your Company'
            vals['copyright_text'] = f'© {year} {company_name}. All rights reserved.'
        return vals

    @api.model
    def get_config(self):
        """Return the single configuration record, creating it on first use.

        Always call with sudo() from public/unauthenticated contexts
        (the login page has no active user session).
        """
        config = self.search([], limit=1, order='id asc')
        if not config:
            config = self.create({})
        return config

    @api.model
    def action_open_config(self):
        """Used by the 'Login Page Theme' menu (via an ir.actions.server) so
        the settings form always opens on the single existing record - or
        creates it on the fly - instead of ever offering a blank 'new
        record' form.
        """
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Login Page Theme',
            'res_model': 'login.theme.config',
            'view_mode': 'form',
            'res_id': config.id,
            'target': 'current',
        }

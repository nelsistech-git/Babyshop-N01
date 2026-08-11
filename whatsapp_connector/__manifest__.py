# -*- coding: utf-8 -*-
# =====================================================================================
# License: OPL-1 (Odoo Proprietary License v1.0)
#
# By using or downloading this module, you agree not to make modifications that
# affect sending messages through Acruxlab or avoiding contract a Plan with Acruxlab.
# Support our work and allow us to keep improving this module and the service!
#
# Al utilizar o descargar este módulo, usted se compromete a no realizar modificaciones que
# afecten el envío de mensajes a través de Acruxlab o a evitar contratar un Plan con Acruxlab.
# Apoya nuestro trabajo y permite que sigamos mejorando este módulo y el servicio!
# =====================================================================================
{
    'name': 'ChatRoom BASE Whatsapp - Messenger - Instagram. Live Chat. Real All in One with ChatGPT OpenAI '
            'and Sale Funnels. Online translator.',
    'summary': 'From ChatRoom main view Search & Send Product. With ChatGPT OpenAI and Sale Funnel. Send message '
               'from many places with Templates (Sale, Invoice, Purchase, CRM Leads, Product, Stock Picking, Partner).'
               ' Like AmoCRM, Kommo, Hubspot, Zendesk. Online translator. Reminders. Text search in messages.'
               ' apichat.io GupShup Chat-Api ChatApi. Whatsapp, Instagram DM, FaceBook Messenger. ChatRoom 2.0.',
    'description': 'Send Product, Real All in One. Send and receive messages. Real ChatRoom. WhatsApp integration. '
                   'WhatsApp Connector. apichat.io. GupShup. Chat-Api. ChatApi. Drag and Drop. ChatRoom 2.0.',
    'version': '17.0.8.1',
    'author': 'AcruxLab',
    'live_test_url': 'https://chatroom.acruxlab.com/web/signup',
    'support': 'info@acruxlab.com',
    'price': 99.2,
    'currency': 'USD',
    'images': ['static/description/Banner_base_v14.gif'],
    'website': 'https://acruxlab.com/plans',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'category': 'Discuss/Sales/CRM',
    'depends': [
        'bus',
        'sales_team',
        'product'
    ],
    'data': [
        'data/data.xml',
        'data/cron.xml',
        'data/ai_config_data.xml',
        'data/mail_activity_type_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/CustomMessage.xml',
        'wizard/init_free_test.xml',
        'wizard/MessageWizard.xml',
        'wizard/ScanQr.xml',
        # 'wizard/SimpleNewConversation.xml',  # eliminar definitivo?
        'views/ir_attachment.xml',
        'views/template_button_views.xml',
        'views/template_list_views.xml',
        'views/default_answer_views.xml',
        'views/connector_views.xml',
        'views/conversation_views.xml',
        'views/conversation_stage_views.xml',
        'views/conversation_tags_views.xml',
        'views/message_views.xml',
        'views/res_partner.xml',
        'views/res_users_views.xml',
        'views/module_views.xml',
        'views/template_waba_views.xml',
        'views/mail_template_views.xml',
        'views/ai_config_views.xml',
        'views/ai_interface_views.xml',
        'views/ai_usage_log_views.xml',
        'views/mail_activity_views.xml',
        'views/conversation_panel_views.xml',
        'wizard/AiInterface.xml',
        'wizard/AiInterfaceTest.xml',
        'reports/report_conversation_views.xml',
        'reports/report_agent_answer_time.xml',
        'reports/reports.xml',
        'views/res_config_settings_views.xml',
        'views/work_queue_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_connector/static/src/scss/*.scss',

            'whatsapp_connector/static/src/odooCore/*/*.xml',

            'whatsapp_connector/static/src/components/*/*.scss',
            'whatsapp_connector/static/src/components/*/*.xml',


            # Chatroom client: split modules (see scripts/split-chatroom-bundle.mjs; vendor blob: chatroom.vendor.bundle.js)
            'whatsapp_connector/static/src/jslib/chatroom_modules/00_attachment.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/01_attachment_list.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/02_notebook_chat.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/03_patch_action_container.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/04_patch_action_dialog.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/05_patch_control_panel.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/06_file_uploader.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/07_patch_form_controller.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/08_patch_kanban_controller.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/09_patch_kanban_renderer.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/10_patch_list_controller.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/11_use_attachment_uploader.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/12_chat_base_model.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/13_conversation_model.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/14_default_answer_model.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/15_message_model.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/16_message_base_model.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/17_product_model.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/18_user_model.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/19_ai_inteface_form.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/20_chatroom_action_tab.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/21_conversation_form.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/22_conversation_kanban.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/23_conversation_panel_form.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/24_partner_form.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/25_audio_player.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/26_chat_search.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/27_chatroom.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/28_chatroom_header.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/29_conversation.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/30_conversation_card.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/31_conversation_header.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/32_conversation_name.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/33_conversation_thread.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/34_conversation_list.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/47_default_answer_send.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/35_default_answer.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/36_emojis.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/37_story_dialog.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/38_message_metadata.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/39_message_options.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/40_product.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/41_product_container.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/42_tabs_container.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/43_activity_button.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/44_toolbox.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/45_chatroom_notification_service.js',
            'whatsapp_connector/static/src/jslib/chatroom_modules/46_register_chatroom_actions.js',
        ],
    },
    'post_load': '',
    'external_dependencies': {'python': ['phonenumbers']},

}

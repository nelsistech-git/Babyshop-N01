# -*- coding: utf-8 -*-

from . import models
from . import wizard


def uninstall_hook(env):
    action = env.ref('account.action_move_journal_line')
    action.write(
        {
            'name': 'Journal Entries',
            'view_mode': 'tree,kanban,form',
            'domain': [],
            'context': {'default_move_type': 'entry', 'search_default_posted': 1, 'view_no_maturity': True}
        })

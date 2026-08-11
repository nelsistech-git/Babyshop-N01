from . import controllers
from . import models
from . import wizard


def _assign_account_parent(env):
    env['account.account']._parent_store_compute()

# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from . import subscription


def register():
    Pool.register(
        subscription.Line,
        subscription.SubscriptionRecomputePriceStart,
        module='sale_subscription_recompute_price', type_='model')
    Pool.register(
        subscription.SubscriptionRecomputePrice,
        module='sale_subscription_recompute_price', type_='wizard')

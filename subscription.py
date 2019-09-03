# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal, ROUND_HALF_UP

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.product.product import price_digits


class Line(metaclass=PoolMeta):
    __name__ = 'sale.subscription.line'

    @classmethod
    def _recompute_price_by_fixed_amount(cls, line, new_unit_price):
        values = {
            'unit_price': new_unit_price,
            }
        return values

    @classmethod
    def recompute_price_by_fixed_amount(cls, lines, unit_price):
        to_write = []
        for line in lines:
            new_values = line._recompute_price_by_fixed_amount(line, unit_price)
            if new_values:
                to_write.extend(([line], new_values))
        if to_write:
            cls.write(*to_write)

    @classmethod
    def _recompute_price_by_percentage(cls, line, factor):
        new_list_price = (line.unit_price * factor).quantize(
            Decimal('1.'), rounding=ROUND_HALF_UP)
        values = {
            'unit_price': new_list_price,
            }
        return values

    @classmethod
    def recompute_price_by_percentage(cls, lines, percentage):
        to_write = []
        factor = Decimal(1) + Decimal(percentage)
        for line in lines:
            new_values = cls._recompute_price_by_percentage(line, factor)
            if new_values:
                to_write.extend(([line], new_values))
        if to_write:
            cls.write(*to_write)


class SubscriptionRecomputePriceStart(ModelView):
    'Recompute Price - Start'
    __name__ = 'sale.subscription.recompute_price.start'
    method = fields.Selection([
            ('fixed_amount', 'Fixed Amount'),
            ('percentage', 'Percentage'),
            ], 'Recompute Method', required=True)
    unit_price = fields.Numeric('Unit Price', digits=price_digits,
        states={
            'invisible': Eval('method') != 'fixed_amount',
            'required': Eval('method') == 'fixed_amount',
            }, depends=['method'])
    date = fields.Date('Date', help="Update running subscriptios up to date",
        required=True)
    subscriptions = fields.Many2Many('sale.subscription', None, None,
        'Subscriptions', domain=[('state', '=', 'running')],
        help="Do not update those Subscriptions.")
    percentage = fields.Float('Percentage', digits=(16, 4),
        states={
            'invisible': Eval('method') != 'percentage',
            'required': Eval('method') == 'percentage',
            },
        depends=['method'])
    categories = fields.Many2Many('product.category', None, None, 'Categories',
        states={
            'invisible': Eval('method') != 'percentage',
            'required': Eval('method') == 'percentage',
            }, depends=['method'])
    services = fields.Many2Many('sale.subscription.service', None, None,
        'Services', states={
            'invisible': Eval('method') != 'fixed_amount',
            'required': Eval('method') == 'fixed_amount',
            }, depends=['method'])

    @staticmethod
    def default_unit_price():
        return Decimal('0')

    @staticmethod
    def default_method():
        return 'fixed_amount'

    #@staticmethod
    #def default_subscriptions():
    #    Contract = Pool().get('contract')
    #    references = ['14466', '14554', '14708', '14788', '14812', '14847', '14854', '14856', '14857', '14902', '14903', '14919', '14970', '14979', '15182', '15280', '14708', '15182']
    #    contracts = Contract.search([('reference', 'in', references)])
    #    return [c.id for c in contracts]


class SubscriptionRecomputePrice(Wizard):
    'Subscription Recompute Price'
    __name__ = 'sale.subscription.recompute_price'

    start = StateView('sale.subscription.recompute_price.start',
        'sale_subscription_recompute_price.recompute_price_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Recompute', 'recompute_', 'tryton-ok', default=True),
            ])
    recompute_ = StateTransition()

    def get_additional_args(self):
        method_name = 'get_additional_args_%s' % self.start.method
        if not hasattr(self, method_name):
            return {}
        return getattr(self, method_name)()

    def get_additional_args_fixed_amount(self):
        return {
            'unit_price': self.start.unit_price,
            }

    def transition_recompute_(self):
        pool = Pool()
        Line = pool.get('sale.subscription.line')

        method_name = 'recompute_price_by_%s' % self.start.method
        method = getattr(Line, method_name)
        if method:
            domain = [
                ('subscription.state', '=', 'running'),
                ('start_date', '<=', self.start.date),
                ('subscription', 'not in', self.start.subscriptions),
                ]
            method(Line.search(domain), **self.get_additional_args())
        return 'end'

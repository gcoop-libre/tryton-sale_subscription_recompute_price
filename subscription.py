# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal, ROUND_HALF_UP

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.product import price_digits


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
            new_values = line._recompute_price_by_fixed_amount(line,
                unit_price)
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
    start_date = fields.Date('Start Date', help="Update running subscriptios"
        " up to date")
    subscriptions = fields.Many2Many('sale.subscription', None, None,
        'Excluded subscriptions', domain=[('state', '=', 'running')],
        help="Do not update those Subscriptions.")
    percentage = fields.Float('Percentage', digits=(16, 4),
        states={
            'invisible': Eval('method') != 'percentage',
            'required': Eval('method') == 'percentage',
            },
        depends=['method'])
    unit_price = fields.Numeric('Unit Price', digits=price_digits,
        states={
            'invisible': Eval('method') != 'fixed_amount',
            'required': Eval('method') == 'fixed_amount',
            }, depends=['method'])
    services = fields.Many2Many('sale.subscription.service', None, None,
        'Services')

    @staticmethod
    def default_unit_price():
        return Decimal('0')

    @staticmethod
    def default_percentage():
        return float(0)

    @staticmethod
    def default_method():
        return 'fixed_amount'

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('/form//label[@id="percentage_"]', 'states', {
                    'invisible': Eval('method') != 'percentage',
                    }),
            ]


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

    def get_additional_args_percentage(self):
        return {
            'percentage': self.start.percentage,
            }

    def transition_recompute_(self):
        pool = Pool()
        Line = pool.get('sale.subscription.line')

        method_name = 'recompute_price_by_%s' % self.start.method
        method = getattr(Line, method_name)
        if method:
            domain = [
                ('subscription.state', '=', 'running'),
                ('subscription', 'not in', self.start.subscriptions),
                ]
            if self.start.start_date:
                domain.append(('start_date', '<=', self.start.start_date))
            if self.start.services:
                services = [s.id for s in list(self.start.services)]
                domain.append(('service', 'in', services))
            method(Line.search(domain), **self.get_additional_args())
        return 'end'

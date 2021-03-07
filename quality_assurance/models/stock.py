# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.depends('move_lines')
    def _compute_alert(self):
        '''
        This function computes the number of quality alerts generated from given picking.
        '''
        for picking in self:
            alerts = self.env['quality.alert'].search([('picking_id', '=', picking.id)])
            picking.alert_ids = alerts
            picking.alert_count = len(alerts)

    def quality_alert_action(self):
        '''This function returns an action that display existing quality alerts generated from a given picking.'''
        action = self.env.ref('quality_assurance.quality_alert_action')
        result = action.read()[0]

        # override the context to get rid of the default filtering on picking type
        result.pop('id', None)
        result['context'] = {}
        alert_ids = sum([picking.alert_ids.ids for picking in self], [])
        # choose the view_mode accordingly
        if len(alert_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, alert_ids)) + "])]"
        elif len(alert_ids) == 1:
            res = self.env.ref('quality_assurance.quality_alert_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = alert_ids and alert_ids[0] or False
        return result

    alert_count = fields.Integer(compute='_compute_alert', string='质检报告', default=0)
    alert_ids = fields.Many2many('quality.alert', compute='_compute_alert', string='质检报告', copy=False)

    def generate_quality_alert(self):
        '''
        This function generates quality alerts for the products mentioned in move_lines of given picking and also have quality measures configured.
        '''
        quality_alert = self.env['quality.alert']
        quality_measure = self.env['quality.measure']
        for move in self.move_lines:
            measures = quality_measure.search([('product_id', '=', move.product_id.id), ('trigger_time', 'in', self.picking_type_id.id)])
            if measures:
                quality_alert.create({
                    'name': self.env['ir.sequence'].next_by_code('quality.alert') or _('New'),
                    'product_id': move.product_id.id,
                    'picking_id': self.id,
                    'origin': self.name,
                    'company_id': self.company_id.id,
                    'date': fields.datetime.now(),
                })

    def action_confirm(self):
        if self.alert_count == 0:
            self.generate_quality_alert()
        res = super(StockPicking, self).action_confirm()
        return res

    def button_validate(self):
        if self.alert_count == 0:
            self.generate_quality_alert()
        res = super(StockPicking, self).button_validate()
        return res

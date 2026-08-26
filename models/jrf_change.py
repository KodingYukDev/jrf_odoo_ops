from odoo import fields, models, _
from odoo.exceptions import UserError


class JrfChange(models.Model):
    _name = 'jrf.change'
    _description = 'JRF Change Request'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(readonly=True, copy=False, default='New', required=True)
    request_id = fields.Many2one('jrf.request', required=True, ondelete='cascade', index=True)
    request_date = fields.Date(default=fields.Date.context_today, required=True)
    requested_by_id = fields.Many2one('hr.employee', default=lambda self: self.env.user.employee_id, required=True)
    description = fields.Html(required=True)
    reason = fields.Text(required=True)
    impact = fields.Text()
    additional_days = fields.Integer()
    new_estimated_completion = fields.Date()
    state = fields.Selection([
        ('proposed', 'Proposed'), ('approved', 'Approved'), ('rejected', 'Rejected')
    ], default='proposed', tracking=True, required=True)
    decision_note = fields.Text(readonly=True)
    decided_by_id = fields.Many2one('hr.employee', readonly=True)
    decided_at = fields.Datetime(readonly=True)

    def _set_number(self):
        for record in self:
            if record.name == 'New' and record.request_id.name != 'Draft':
                siblings = self.search_count([('request_id', '=', record.request_id.id)])
                record.name = '%s-CR%02d' % (record.request_id.name.replace('/', '-'), siblings)

    def action_approve(self):
        for record in self:
            if record.state != 'proposed':
                raise UserError(_('Only a proposed change request can be approved.'))
            record._set_number()
            record.write({
                'state': 'approved', 'decided_by_id': self.env.user.employee_id.id,
                'decided_at': fields.Datetime.now(),
            })
            if record.new_estimated_completion:
                record.request_id.estimated_completion = record.new_estimated_completion
            record.request_id.message_post(body=_('Change request %s approved.') % record.name)

    def action_reject(self):
        for record in self:
            if record.state != 'proposed':
                raise UserError(_('Only a proposed change request can be rejected.'))
            record._set_number()
            record.write({
                'state': 'rejected', 'decided_by_id': self.env.user.employee_id.id,
                'decided_at': fields.Datetime.now(),
            })

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    jrf_code = fields.Char(string='JRF Code', help='Short code used in JRF numbers, e.g. IT, MKT, ACD.')


class JrfRequest(models.Model):
    _name = 'jrf.request'
    _description = 'Job Request Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='JRF Number', default='Draft', readonly=True, copy=False, required=True, tracking=True)
    request_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    requester_id = fields.Many2one('hr.employee', string='Requester', required=True, default=lambda self: self.env.user.employee_id, tracking=True)
    requester_department_id = fields.Many2one('hr.department', string='Requester Department', readonly=True, tracking=True)
    target_department_id = fields.Many2one('hr.department', string='Target Department', required=True, tracking=True, ondelete='restrict')
    category = fields.Selection([
        ('general', 'General Work'), ('system', 'System / Automation'), ('design', 'Design / Creative'),
        ('marketing', 'Marketing'), ('academic', 'Academic'), ('other', 'Other')
    ], default='general', required=True, tracking=True)
    title = fields.Char(required=True, tracking=True)
    description = fields.Html(required=True)
    business_purpose = fields.Html(required=True)
    expected_output = fields.Html(required=True)
    priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('critical', 'Critical')
    ], default='normal', required=True, tracking=True)
    priority_reason = fields.Text(tracking=True)
    requested_target_date = fields.Date(string='Requested Target', tracking=True)
    assigned_pic_id = fields.Many2one('hr.employee', string='Assigned PIC', tracking=True)
    support_pic_ids = fields.Many2many('hr.employee', 'jrf_request_support_employee_rel', string='Support PIC')
    accepted_date = fields.Datetime(readonly=True, copy=False)
    estimated_completion = fields.Date(tracking=True)
    pic_notes = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'), ('waiting_requester', 'Waiting for Requester'), ('review', 'Review'),
        ('completed', 'Completed'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')
    ], default='draft', required=True, tracking=True, copy=False)
    waiting_for_department_id = fields.Many2one('hr.department', string='Waiting For')
    waiting_since = fields.Datetime(readonly=True, copy=False)
    waiting_reason = fields.Text()
    completion_notes = fields.Html()
    result_url = fields.Char()
    repository_url = fields.Char()
    deployment_url = fields.Char()
    review_submitted_at = fields.Datetime(readonly=True, copy=False)
    accepted_by_id = fields.Many2one('hr.employee', readonly=True, copy=False)
    accepted_at = fields.Datetime(readonly=True, copy=False)
    acceptance_notes = fields.Text()
    rejection_reason = fields.Text()
    change_ids = fields.One2many('jrf.change', 'request_id', string='Change Requests')
    is_requester = fields.Boolean(compute='_compute_roles')
    is_target_head = fields.Boolean(compute='_compute_roles')

    @api.depends('requester_id', 'target_department_id')
    def _compute_roles(self):
        employee = self.env.user.employee_id
        for record in self:
            record.is_requester = record.requester_id == employee
            record.is_target_head = record.target_department_id.manager_id == employee

    @api.onchange('requester_id')
    def _onchange_requester_id(self):
        self.requester_department_id = self.requester_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            employee = self.env['hr.employee'].browse(vals.get('requester_id')) if vals.get('requester_id') else self.env.user.employee_id
            vals.setdefault('requester_department_id', employee.department_id.id)
        return super().create(vals_list)

    @api.constrains('priority', 'priority_reason')
    def _check_priority_reason(self):
        for record in self:
            if record.priority in ('high', 'critical') and not record.priority_reason:
                raise ValidationError(_('Priority reason is required for High or Critical requests.'))

    def _assign_number(self):
        for record in self:
            if record.name != 'Draft':
                continue
            department = record.target_department_id
            if not department:
                raise UserError(_('Target Department is required before submission.'))
            code = (department.jrf_code or department.name[:3] or 'GEN').upper().replace(' ', '')
            sequence_code = 'jrf.request.%s.%s' % (self.env.company.id, department.id)
            self.env.cr.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', [sequence_code])
            sequence = self.env['ir.sequence'].sudo().search([('code', '=', sequence_code)], limit=1)
            if not sequence:
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': 'JRF %s' % code, 'code': sequence_code, 'padding': 4,
                    'implementation': 'no_gap', 'use_date_range': True, 'company_id': self.env.company.id,
                })
            sequence_number = sequence.next_by_id(sequence_date=record.request_date) or '0000'
            record.name = 'JRF/%s/%s/%s' % (code, record.request_date.year, sequence_number)

    def action_submit(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only Draft JRF can be submitted.'))
            record._assign_number()
            record.write({'state': 'submitted'})
            record.message_post(body=_('JRF submitted to %s.') % record.target_department_id.name)

    def action_approve(self):
        self._ensure_target_head()
        self.write({'state': 'approved', 'accepted_date': fields.Datetime.now()})

    def action_assign(self):
        self._ensure_target_head()
        for record in self:
            if not record.assigned_pic_id:
                raise UserError(_('Assign a PIC before assigning the JRF.'))
        self.write({'state': 'assigned'})

    def action_start(self):
        for record in self:
            if not record.assigned_pic_id:
                raise UserError(_('Assign a PIC before starting the work.'))
        self.write({'state': 'in_progress'})

    def action_wait_requester(self):
        for record in self:
            if not record.waiting_for_department_id or not record.waiting_reason:
                raise UserError(_('Waiting For and Waiting Reason are required.'))
            record.write({'state': 'waiting_requester', 'waiting_since': fields.Datetime.now()})

    def action_resume(self):
        self.write({'state': 'in_progress', 'waiting_since': False})

    def action_submit_review(self):
        for record in self:
            if not record.completion_notes:
                raise UserError(_('Completion Notes are required before review.'))
            if not (record.result_url or record.repository_url or record.deployment_url or record.message_attachment_count):
                raise UserError(_('Provide at least one result URL, repository URL, deployment URL, or attachment.'))
            record.write({'state': 'review', 'review_submitted_at': fields.Datetime.now()})

    def action_accept(self):
        for record in self:
            if record.state != 'review':
                raise UserError(_('Only JRF in Review can be accepted.'))
            if record.requester_id != self.env.user.employee_id and not self.env.user.has_group('jrf_odoo_ops.group_jrf_management'):
                raise UserError(_('Only the requester or Management may accept this JRF.'))
            record.write({'state': 'completed', 'accepted_by_id': self.env.user.employee_id.id, 'accepted_at': fields.Datetime.now()})

    def action_request_revision(self):
        for record in self:
            if record.state != 'review':
                raise UserError(_('Only JRF in Review can be returned for revision.'))
            record.write({'state': 'in_progress'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _ensure_target_head(self):
        for record in self:
            if record.target_department_id.manager_id != self.env.user.employee_id and not self.env.user.has_group('jrf_odoo_ops.group_jrf_management'):
                raise UserError(_('Only the Target Department Head or Management may perform this action.'))

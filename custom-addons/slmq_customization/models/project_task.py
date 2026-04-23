from odoo import models, api


class ProjectTask(models.Model):
    _inherit = 'project.task'


    @api.model
    def create(self, vals):
        task = super().create(vals)

        # Get Project Manager group users
        group = self.env.ref('project.group_project_manager')
        users = group.user_ids.filtered(lambda u: u.email)

        template = self.env.ref('slmq_customization.task_notify_pm_template')

        for user in users:
            template.send_mail(task.id, force_send=True, email_values={'email_to': user.email})

        return task


    def write(self, vals):

        res = super().write(vals)

        # Get Project Manager group users
        group = self.env.ref('project.group_project_manager')
        users = group.user_ids.filtered(lambda u: u.email)
        
        template_done = self.env.ref('slmq_customization.task_done_mail_template')

        for task in self:

            # ✅ 1. Task moved to Done
            if vals.get('state') == '1_done':

                for user in users:
                    template_done.send_mail(task.id, force_send=True, email_values={'email_to': user.email})

        return res
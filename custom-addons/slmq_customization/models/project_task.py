from odoo import models, api


class ProjectTask(models.Model):
    _inherit = 'project.task'


    def write(self, vals):

        res = super().write(vals)
        
        template_done = self.env.ref('slmq_customization.task_done_mail_template')

        for task in self:

            # ✅ 1. Task moved to Done
            if vals.get('state') == '1_done':

                manager = task.project_id.user_id
                if manager and manager.email:

                    template_done.send_mail(
                        task.id,
                        force_send=True,
                        email_values={'email_to': manager.email}
                    )

        return res
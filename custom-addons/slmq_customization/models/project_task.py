from odoo import models, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.model
    def create(self, vals):
        task = super().create(vals)

        if task.user_ids:
            template = self.env.ref('slmq_customization.task_assign_mail_template')

            for user in task.user_ids:
                if user.email:

                    template.with_context(
                        user_name=user.name
                    ).send_mail(
                        task.id,
                        force_send=True,
                        email_values={'email_to': user.email}
                    )

        return task

    def write(self, vals):
        old_users_map = {task.id: task.user_ids for task in self}

        res = super().write(vals)

        template_assign = self.env.ref('slmq_customization.task_assign_mail_template')
        template_done = self.env.ref('slmq_customization.task_done_mail_template')

        for task in self:

            # ✅ 1. Newly assigned users
            if 'user_ids' in vals:
                old_users = old_users_map.get(task.id, self.env['res.users'])
                new_users = task.user_ids - old_users

                for user in new_users:
                    if user.email:
                        template_assign.send_mail(
                            task.id,
                            force_send=True,
                            email_values={'email_to': user.email}
                        )

            # ✅ 2. Task moved to Done
            if vals.get('state') == '1_done':

                manager = task.project_id.user_id
                if manager and manager.email:

                    template_done.send_mail(
                        task.id,
                        force_send=True,
                        email_values={'email_to': manager.email}
                    )

        return res
{
    'name': 'SLMQ Customisation',
    'version': '19.0.0.1',
    'license': 'LGPL-3', 
    'author': 'FSIB',

    'summary': 'Membership management with approval workflow and automated user onboarding',

    'description': """
            Membership Management Module

            This module provides a complete solution to manage the membership lifecycle,
            including registration, approval, communication, and user access creation.

            Key Features:
            - Membership registration from website and backend
            - Parent-child relationship handling for memberships
            - Approval workflow with manager validation
            - Automatic user creation upon approval

            Approval Process:
            1. A user submits a membership request via website or backend.
            2. The membership is reviewed by a manager.
            3. The manager can approve or reject the request.

            This module ensures a structured and automated approach to handling memberships
            with minimal manual intervention.
    """,

    'depends': ['website','contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/mail_template.xml',
        'views/membership_views.xml',
        'views/res_partner_views.xml'
    ],
    'installable': True,
}
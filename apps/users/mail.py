from djoser import email


class ConfirmationEmail(email.ConfirmationEmail):
    template_name = "mail/confirmation.html"


class PasswordResetEmail(email.PasswordResetEmail):
    template_name = "mail/password_reset.html"


class PasswordChangedConfirmationEmail(
    email.PasswordChangedConfirmationEmail
):
    template_name = "mail/password_changed_confirmation.html"
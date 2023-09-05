from djoser import utils
from djoser import email
from djoser.conf import settings
from templated_mail.mail import BaseEmailMessage
from django.contrib.auth.tokens import default_token_generator


class ConfirmationEmail(BaseEmailMessage):
    template_name = "mail/confirmation.html"


class PasswordResetEmail(BaseEmailMessage):
    template_name = "mail/password_reset.html"

    def get_context_data(self):
        # PasswordResetEmail can be deleted
        context = super().get_context_data()

        user = context.get("user")
        context["uid"] = utils.encode_uid(user.pk) # type:ignore
        context["token"] = default_token_generator.make_token(user)
        context["url"] = settings.PASSWORD_RESET_CONFIRM_URL.format(**context) # type: ignore
        return context

class PasswordChangedConfirmationEmail(BaseEmailMessage):
    template_name = "mail/password_changed_confirmation.html"





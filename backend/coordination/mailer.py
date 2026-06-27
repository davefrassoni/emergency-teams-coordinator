from django.conf import settings
from django.core.mail import EmailMessage, send_mail


def send_magic_login(email, operation_name, codename, login_url):
    return send_mail(
        f"Sign in to {operation_name} · ReliefGrid",
        (
            f"Use this one-time link to sign in as an administrator for "
            f"{operation_name} ({codename}):\n\n{login_url}\n\n"
            "The link expires in 20 minutes. If you did not request it, ignore this email."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


def send_feature_request(contact_email, message, page_url, locale):
    email = EmailMessage(
        subject="ReliefGrid feature request",
        body=(
            f"Contact: {contact_email}\n"
            f"Locale: {locale or 'unknown'}\n"
            f"Page: {page_url or 'unknown'}\n\n{message}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.FEATURE_REQUEST_EMAIL],
        reply_to=[contact_email],
    )
    return email.send(fail_silently=False)

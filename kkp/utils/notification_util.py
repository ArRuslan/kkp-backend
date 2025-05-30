from email.message import EmailMessage

from loguru import logger

from kkp.config import SMTP, FCM
from kkp.models import User, Session


async def send_notification(user: User, title: str, text: str, email: bool = True, fcm: bool = True) -> None:
    if email:
        message = EmailMessage()
        message["From"] = "kkp@example.com"
        message["To"] = user.email
        message["Subject"] = title
        message.set_content(text)

        try:
            await SMTP.send_message(message, timeout=5)
        except Exception as e:  # pragma: no cover
            logger.opt(exception=e).error(f"Failed to send email to {email}!")

    if fcm:
        for session in await Session.filter(user=user, fcm_token__not_isnull=True).order_by("-fcm_token_time").limit(10):
            try:
                await FCM.send_notification(title, text, device_token=session.fcm_token)
            except Exception as e:
                logger.opt(exception=e).warning(
                    f"Failed to send notification to session {session.id} ({session.fcm_token!r})"
                )

from email.message import EmailMessage

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
            await SMTP.send(message, timeout=5)
        except Exception as e:
            ...  # TODO: log error

    if fcm:
        for session in await Session.filter(user=user, fcm_token__not=None).order_by("-fcm_token_time").limit(10):
            try:
                await FCM.send_notification(title, text, device_token=session.fcm_token)
            except Exception as e:
                ...  # TODO: log error

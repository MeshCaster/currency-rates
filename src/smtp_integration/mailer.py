import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Literal

from anyio import to_thread

from smtp_integration.errors import EmailDeliveryError

type Security = Literal["starttls", "ssl", "none"]


class SmtpMailer:

    def __init__(self, host: str, port: int = 587, *, security: Security = "starttls",
                 username: str | None = None, password: str | None = None,
                 from_address: str = "Currency Rates <no-reply@localhost>",
                 timeout: float = 30.0) -> None:
        self._host, self._port, self._security = host, port, security
        self._username, self._password = username, password
        self._from = from_address
        self._timeout = timeout

    async def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self._from, to, subject
        message["Message-ID"] = make_msgid(domain=self._from.rsplit("@", 1)[-1].strip("> "))
        message.set_content(text)
        if html is not None:
            message.add_alternative(html, subtype="html")
        await to_thread.run_sync(self._deliver, message)

    def _deliver(self, message: EmailMessage) -> None:
        try:
            if self._security == "ssl":
                smtp: smtplib.SMTP = smtplib.SMTP_SSL(
                    self._host, self._port, timeout=self._timeout,
                    context=ssl.create_default_context())
            else:
                smtp = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
            with smtp:
                if self._security == "starttls":
                    smtp.starttls(context=ssl.create_default_context())
                if self._username:
                    smtp.login(self._username, self._password or "")
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as e:
            raise EmailDeliveryError(
                f"SMTP {self._host}:{self._port} failed: {type(e).__name__}: {e}") from e

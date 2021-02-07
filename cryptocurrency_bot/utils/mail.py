import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Lock

from configs.EMAIL import EMAIL_ADDRESS, EMAIL_PASSWORD


port = 465  # For SSL
# Create a secure SSL context
context = ssl.create_default_context()


def send_mail(text:str, to_email:str=EMAIL_ADDRESS, html:str=None, subject:str=None):
    with Lock():
        message = MIMEMultipart("alternative") if html else MIMEMultipart()
        message['Subject'] = subject or "Techsupport message"
        message['From'] = EMAIL_ADDRESS
        message['To'] = to_email
        text_part = MIMEText(text, "plain")
        message.attach(text_part)
        if html:
            html_part = MIMEText(html, 'html')
            message.attach(html_part)
        with smtplib.SMTP_SSL(host='smtp.gmail.com', port=port, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(
                    EMAIL_ADDRESS, to_email, message.as_string()
                )


if __name__ == '__main__':
    send_mail('Hey, nice mailing!', subject='Test')
import os 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(reciever : str, subject: str, body: str, sender = "kumarrohitindia25@gmail.com"):
     msg = MIMEMultipart()
     msg["From"] = sender
     msg["To"] = reciever
     msg["Subject"] = "Sales email"

     body = "Hello, this is a test email sent from Python!"
     msg.attach(MIMEText(body, "plain"))

     with smtplib.SMTP("smtp.gmail.com", 587) as server:
          server.starttls()
          server.login(sender, os.environ("APP_PASSWORD"))
          server.send_message(msg)
     
     print("✅ Email sent successfully!")
     
     
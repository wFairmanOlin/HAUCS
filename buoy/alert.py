import smtplib
import json
from email.message import EmailMessage
import time

BUOY_ID = 1
folder = ""
body = "new test today"

with open(folder + "email_cred.json") as file:
    cred = json.load(file)

msg = EmailMessage()
msg['Subject'] = "NABuoy " + str(BUOY_ID)
msg['From'] = cred['from']
msg['To'] = ', '.join(cred['to'])

#get local time
content = f"{time.strftime('%I:%M %p', time.localtime())}\n"
content += f"battery: {13.22}\npond: {'unknown'}\n"
content += body
msg.set_content(content)
server = smtplib.SMTP("smtp.gmail.com", 587)
# server.ehlo()
server.starttls()
server.login(cred['user'], cred['pwd'])
server.send_message(msg)
server.close()

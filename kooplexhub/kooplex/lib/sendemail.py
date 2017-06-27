import smtplib
from email.mime.text import MIMEText

#FIXME: how to import this variable?
#from kooplex.lib.settings import KOOPLEX_BASE_URL
KOOPLEX_BASE_URL = "https://kooplex.vo.elte.hu"


def send_new_password(name, username, to, pw):
    content = """
Dear %s,

your new kooplex account (%s) is created.

The login password is set %s . Please change it the first time you visit the dasboard at %s.

Best regards,
 Kooplex team
    """ % (name, username, pw, KOOPLEX_BASE_URL)

    smtp_server = 'mail.elte.hu' #FIXME: hardcoded


    msg = MIMEText(content)
    msg['Subject'] = 'Your kooplex account is created'
    msg['From'] = 'kooplex@complex.elte.hu'
    msg['To'] = to

    try:
        s = smtplib.SMTP(smtp_server)
        s.send_message(msg)
        s.quit()
        return
    except Exception as e:
        pass
    finally:
        with open('/tmp/%s', 'w') as f:
            f.write(pw)

    content = """
Instance: %s
Kooplex account: %s %s
Name: %s (%s)
Failure to deliver mail: %s
    """ % (KOOPLEX_BASE_URL, username, pw, name, to, e)

    msg = MIMEText(content)
    msg['Subject'] = 'Kooplex account details not delivered'
    msg['From'] = 'kooplex@complex.elte.hu'
    msg['To'] = 'kooplex@complex.elte.hu'

    try:
        s = smtplib.SMTP(smtp_server)
        s.send_message(msg)
        s.quit()
    except:
        pass
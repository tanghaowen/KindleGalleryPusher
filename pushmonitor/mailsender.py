import smtplib,os,sys
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr


smtp_username = 'admin@lpanda.net'
smtp_password = 'shinonomehana'
smtp_hostname = 'smtp.lpanda.net'


def send_mail_use_smtp(reciviers_adress,file_url,file_name):
    print("开始登陆邮箱SMTP...")
    print("  ",smtp_username)
    print("  To:", reciviers_adress)
    server = smtplib.SMTP_SSL(smtp_hostname, 465)  # 发件人邮箱中的SMTP服务器，端口是25
    server.login(smtp_username, smtp_password)  # 括号中对应的是发件人邮箱账号、邮箱密码
    print("登陆成功")
    msg = MIMEMultipart()
    msg['From'] = formataddr(["ManTui", smtp_username])  # 括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['Subject'] = file_name  # 邮件的主题，也可以说是标题

    f = open(file_url,'rb')
    att1 = MIMEText(f.read(), 'base64', 'utf-8')
    f.close()
    att1["Content-Type"] = 'application/octet-stream'
    att1.add_header('Content-Disposition', 'attachment', filename=file_name)
    print("使用附件名%s" % file_name)
    msg.attach(att1)
    print("开始编码为string...")
    msg_string = msg.as_string()
    print("编码完成，整体大小%.2fMB" % (len(msg_string)/1024.0/1024))
    print("开始发送...")
    server.sendmail(smtp_username, reciviers_adress, msg_string)  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
    print("发送完成")
    server.close()
    return True

if __name__ == '__main__':
    send_mail_use_smtp(['ueinohakono@kindle.com'],
                       r"E:\Project\KindleComicPusher\media\books\川柳少女\五十嵐正邦_川柳少女_第04巻.mobi",
                       '樱花庄.mobi')

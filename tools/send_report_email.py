#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送「法规雷达月报」(HTML)——自建邮局 SMTP 直发,保真、图片内嵌为 CID。

为什么用它:自建邮局(如 1clicktong.com)可直接用 SMTP 把 HTML 作为邮件正文发出,
绕过网页写信框的样式清洗;并把远程图片下载后以 CID 内嵌,收件人无需点「显示远程图片」。

凭据从环境变量读取(不要把密码写进代码/仓库):
    export SMTP_HOST=mail.1clicktong.com     # 若发信服务器不同可改,如 smtp.1clicktong.com
    export SMTP_PORT=465                      # 465=SSL(默认);587=STARTTLS
    export SMTP_USER=support@mail.1clicktong.com
    export SMTP_PASS=********                 # 邮箱密码或授权码

用法:
    python3 tools/send_report_email.py reports/radar-monthly-2026-06.html \
        --to "a@x.com,b@y.com" \
        --subject "一点通 · 全球汽车法规雷达月报 2026年6月刊"

可选:
    --from-name "一点通 1ClickTong"   发件人显示名
    --no-inline-images                不内嵌图片(保留远程外链,收件人需手动显示图片)
    --dry-run                         只组装不发送,打印邮件大小与图片数,便于自检
"""
import os, sys, ssl, smtplib, argparse, re, mimetypes, urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import make_msgid, formataddr, formatdate


def build_message(html, subject, sender, from_name, to_list, inline_images=True):
    root = MIMEMultipart("related")
    root["Subject"] = subject
    root["From"] = formataddr((from_name, sender))
    root["To"] = ", ".join(to_list)
    root["Date"] = formatdate(localtime=True)
    root["Message-ID"] = make_msgid(domain=sender.split("@")[-1])

    images = []
    if inline_images:
        seen = {}

        def repl(m):
            pre, url, post = m.group(1), m.group(2), m.group(3)
            if not url.lower().startswith("http"):
                return m.group(0)
            if url not in seen:
                try:
                    data = urllib.request.urlopen(url, timeout=25).read()
                except Exception as e:
                    print("  ! 图片下载失败,保留外链:", url, e)
                    return m.group(0)
                ctype = mimetypes.guess_type(url)[0] or "image/jpeg"
                subtype = ctype.split("/")[-1]
                cid = make_msgid(domain=sender.split("@")[-1])[1:-1]
                img = MIMEImage(data, _subtype=subtype)
                img.add_header("Content-ID", "<%s>" % cid)
                img.add_header("Content-Disposition", "inline")
                images.append(img)
                seen[url] = "cid:" + cid
                print("  + 内嵌图片:", url)
            return pre + seen[url] + post

        html = re.sub(r'(<img[^>]+?src=")([^"]+)(")', repl, html, flags=re.I)

    alt = MIMEMultipart("alternative")
    root.attach(alt)
    alt.attach(MIMEText("本邮件为 HTML 月报,请用支持 HTML 的邮件客户端查看。", "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    for img in images:
        root.attach(img)
    return root, len(images)


def main():
    ap = argparse.ArgumentParser(description="自建邮局 SMTP 直发月报 HTML(图片内嵌 CID)")
    ap.add_argument("html", help="月报 HTML 文件路径,如 reports/radar-monthly-2026-06.html")
    ap.add_argument("--to", required=True, help="收件人,多个用逗号分隔")
    ap.add_argument("--subject", default="一点通 · 全球汽车法规雷达月报")
    ap.add_argument("--from-name", default="一点通 1ClickTong")
    ap.add_argument("--no-inline-images", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    with open(a.html, encoding="utf-8") as f:
        html = f.read()
    to_list = [x.strip() for x in a.to.split(",") if x.strip()]

    if a.dry_run:
        sender = os.environ.get("SMTP_USER", "support@mail.1clicktong.com")
        msg, nimg = build_message(html, a.subject, sender, a.from_name, to_list,
                                   inline_images=not a.no_inline_images)
        raw = msg.as_string()
        print("[dry-run] 收件人:", to_list)
        print("[dry-run] 内嵌图片:", nimg, "张")
        print("[dry-run] 邮件大小:", round(len(raw.encode("utf-8")) / 1024, 1), "KB")
        return

    try:
        host = os.environ["SMTP_HOST"]
        user = os.environ["SMTP_USER"]
        pw = os.environ["SMTP_PASS"]
    except KeyError as e:
        sys.exit("缺少环境变量 %s;请先 export SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS" % e)
    port = int(os.environ.get("SMTP_PORT", "465"))

    msg, nimg = build_message(html, a.subject, user, a.from_name, to_list,
                              inline_images=not a.no_inline_images)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx) as s:
            s.login(user, pw)
            s.sendmail(user, to_list, msg.as_string())
    else:
        with smtplib.SMTP(host, port) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.login(user, pw)
            s.sendmail(user, to_list, msg.as_string())
    print("已发送 → %s(内嵌图片 %d 张)" % (", ".join(to_list), nimg))


if __name__ == "__main__":
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
Notification module.
"""


import smtplib
import sys
import optparse

import kobo.shortcuts


class EmailNotification(object):
    """Send notification e-mails."""

    def __init__(self, smtp_host):
        # connect to SMTP server
        self.smtp_host = smtp_host
        self.server = smtplib.SMTP(smtp_host)

    def __del__(self):
        # disconnect from SMTP server
        self.server.quit()

    def send(self, from_addr, recipients, subject, body, reply_to=None, xheaders=None):
        """send a notification"""
        recipients = kobo.shortcuts.force_list(recipients)
        xheaders = xheaders or {}

        for to_addr in recipients:
            headers = []
            headers.append("From: %s" % from_addr)
            headers.append("Subject: %s" % subject)
            headers.append("To: %s" % to_addr)
            if reply_to:
                headers.append("Reply-To: %s" % reply_to)

            for key, value in xheaders.iteritems():
                if not key.startswith("X-"):
                    raise KeyError("X-Header has to start with 'X-': %s" % key)
                headers.append("%s: %s" % (key, value))

            headers.append("") # blank line after headers
            headers.append(body)

            message = "\r\n".join(headers)
            self.server.sendmail(from_addr, to_addr, message)


def main(argv):
    """Main function for command line usage"""
    parser = optparse.OptionParser("usage: %prog <options> <to_addr> [to_addr]...")
    parser.add_option(
        "--server",
        help="specify SMTP server address"
    )
    parser.add_option(
        "-f",
        "--from",
        dest="from_addr",
        help="set the From address"
    )
    parser.add_option(
        "-s",
        "--subject",
        help="set email Subject"
    )
    parser.add_option(
        "-r",
        "--reply-to",
        help="set the Reply-To address"
    )
    parser.add_option(
        "-x",
        "--xheader",
        nargs=2,
        dest="xheaders",
        action="append",
        help="set X-Headers; takes two arguments (-x X-Spam eggs)"
    )

    (opts, args) = parser.parse_args(argv)

    server = opts.server
    from_addr = opts.from_addr
    subject = opts.subject
    reply_to = opts.reply_to
    xheaders = opts.xheaders and dict(opts.xheaders) or {}
    recipients = args

    if not server:
        parser.error("SMTP server address required")

    if not from_addr or "@" not in from_addr:
        parser.error("invalid From address: %s" % from_addr)

    if not subject:
        parser.error("empty Subject")

    if len(recipients) == 0:
        parser.error("at least one recipient required")

    for to_addr in recipients:
        if "@" not in to_addr:
            parser.error("invalid To address: %s" % to_addr)

    for key in xheaders:
        if not key.startswith("X-"):
            parser.error("X-Header has to start with 'X-': %s" % key)

    notify = EmailNotification(server)
    body = sys.stdin.read()
    notify.send(from_addr, recipients, subject, body, reply_to=reply_to, xheaders=xheaders)


if __name__ == "__main__":
    main(sys.argv[1:])

"""SMTP email backend class."""
import smtplib
import ssl
import threading

from django.utils.unsetting import uses_settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.utils import DNS_NAME
from django.core.mail.message import sanitize_address
from django.utils.encoding import force_bytes


class EmailBackend(BaseEmailBackend):
    """
    A wrapper that manages the SMTP network connection.
    """
    @uses_settings({'EMAIL_HOST':'email_host', 'EMAIL_PORT':'email_port', 'EMAIL_HOST_USER':'email_host_user', 'EMAIL_HOST_PASSWORD':'email_host_password', 'EMAIL_USE_TLS':'email_use_tls', 'EMAIL_USE_SSL':'email_use_ssl'})
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, email_host='localhost', email_port=25, email_host_user='', email_host_password='', email_use_tls=False, email_use_ssl=False, **kwargs):
        super(EmailBackend, self).__init__(fail_silently=fail_silently)
        self.host = host or email_host
        self.port = port or email_port
        self.username = email_host_user if username is None else username
        self.password = email_host_password if password is None else password
        self.use_tls = email_use_tls if use_tls is None else use_tls
        self.use_ssl = email_use_ssl if use_ssl is None else use_ssl
        if self.use_ssl and self.use_tls:
            raise ValueError(
                "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
                "one of those settings to True.")
        self.connection = None
        self._lock = threading.RLock()

    def open(self):
        """
        Ensures we have a connection to the email server. Returns whether or
        not a new connection was required (True or False).
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False
        try:
            # If local_hostname is not specified, socket.getfqdn() gets used.
            # For performance, we use the cached FQDN for local_hostname.
            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(self.host, self.port,
                                           local_hostname=DNS_NAME.get_fqdn())
            else:
                self.connection = smtplib.SMTP(self.host, self.port,
                                           local_hostname=DNS_NAME.get_fqdn())
                # TLS/SSL are mutually exclusive, so only attempt TLS over
                # non-secure connections.
                if self.use_tls:
                    self.connection.ehlo()
                    self.connection.starttls()
                    self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except:
            if not self.fail_silently:
                raise

    def close(self):
        """Closes the connection to the email server."""
        if self.connection is None:
            return
        try:
            try:
                self.connection.quit()
            except (ssl.SSLError, smtplib.SMTPServerDisconnected):
                # This happens when calling quit() on a TLS connection
                # sometimes, or when the connection was already disconnected
                # by the server.
                self.connection.close()
            except:
                if self.fail_silently:
                    return
                raise
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        if not email_messages:
            return
        with self._lock:
            new_conn_created = self.open()
            if not self.connection:
                # We failed silently on open().
                # Trying to send would be pointless.
                return
            num_sent = 0
            for message in email_messages:
                sent = self._send(message)
                if sent:
                    num_sent += 1
            if new_conn_created:
                self.close()
        return num_sent

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        from_email = sanitize_address(email_message.from_email, email_message.encoding)
        recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in email_message.recipients()]
        message = email_message.message()
        charset = message.get_charset().get_output_charset() if message.get_charset() else 'utf-8'
        try:
            self.connection.sendmail(from_email, recipients,
                    force_bytes(message.as_string(), charset))
        except:
            if not self.fail_silently:
                raise
            return False
        return True

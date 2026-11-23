import queue
import socket
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


DNS_TIMEOUT_SECONDS = 5
TCP_TIMEOUT_SECONDS = 5
POSTGRES_TIMEOUT_SECONDS = 10


class Command(BaseCommand):
    help = "Safely diagnose the configured PostgreSQL connection."

    def handle(self, *args, **options):
        if settings.USE_SQLITE:
            database_path = Path(settings.DATABASES["default"]["NAME"])
            try:
                if database_path.exists():
                    with database_path.open("r+b"):
                        pass
                else:
                    with tempfile.NamedTemporaryFile(
                        dir=database_path.parent,
                        prefix=".sugarlert-db-write-check-",
                    ):
                        pass
            except OSError as error:
                raise CommandError(
                    f"SQLite mode active, but the database location is not writable: {error}"
                ) from error
            self.stdout.write("SQLite mode active, skipping network checks.")
            self.stdout.write(f"SQLite database location is writable: {database_path}")
            return

        database_url = settings.DATABASE_URL
        parsed_url = urlsplit(database_url)
        host = parsed_url.hostname
        port = parsed_url.port or 5432
        username = unquote(parsed_url.username or "(not set)")
        if not host:
            raise CommandError("DATABASE_URL does not contain a valid hostname.")

        self.stdout.write(f"Target: postgresql://{username}@{host}:{port}")
        addresses, dns_errors, dns_timed_out = self._resolve(host)
        if addresses:
            ipv4 = sorted({address[4][0] for address in addresses if address[0] == socket.AF_INET})
            ipv6 = sorted({address[4][0] for address in addresses if address[0] == socket.AF_INET6})
            self.stdout.write(f"A (IPv4): {', '.join(ipv4) if ipv4 else 'none'}")
            self.stdout.write(f"AAAA (IPv6): {', '.join(ipv6) if ipv6 else 'none'}")
        elif dns_timed_out:
            self.stderr.write("DNS: timed out after 5 seconds.")
        else:
            reason = "; ".join(str(error) for error in dns_errors) or "no records returned"
            self.stderr.write(f"DNS: resolution failed ({reason}).")

        if not addresses:
            self.stderr.write("TCP: skipped because DNS returned no A/AAAA addresses.")

        ipv4 = any(address[0] == socket.AF_INET for address in addresses)
        ipv6 = any(address[0] == socket.AF_INET6 for address in addresses)
        if ipv6 and not ipv4:
            self.stderr.write(
                "Diagnosis: this hostname resolves only to IPv6. Prefer the "
                "Supabase Session pooler on port 5432 for IPv4-compatible access."
            )

        tcp_result, tcp_error = (
            self._tcp_connect(addresses, port)
            if addresses
            else (None, "skipped because DNS returned no A/AAAA addresses")
        )
        if tcp_result:
            self.stdout.write(f"TCP: connected over {tcp_result}.")
        elif addresses:
            self.stderr.write(f"TCP: failed ({tcp_error}).")

        try:
            with psycopg.connect(
                database_url,
                connect_timeout=POSTGRES_TIMEOUT_SECONDS,
                sslmode="require",
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
        except psycopg.Error as error:
            diagnosis, next_step = self._diagnosis(
                error,
                tcp_result,
                ipv4,
                ipv6,
                dns_failed=not addresses,
                dns_timed_out=dns_timed_out,
            )
            self.stderr.write(f"PostgreSQL: failed ({error.__class__.__name__}: {error}).")
            self.stderr.write(f"Diagnosis: {diagnosis}")
            self.stderr.write(f"Next step: {next_step}")
            raise CommandError("PostgreSQL connection check failed.") from error

        if result != (1,):
            raise CommandError("PostgreSQL connected, but SELECT 1 returned an unexpected result.")
        self.stdout.write("PostgreSQL: connected; SELECT 1 returned 1.")

    @staticmethod
    def _resolve(host):
        results = queue.Queue()

        def resolve_family(family):
            try:
                result = socket.getaddrinfo(host, None, family, socket.SOCK_STREAM)
                results.put((family, result, None))
            except socket.gaierror as error:
                results.put((family, [], error))

        threads = [
            threading.Thread(target=resolve_family, args=(family,), daemon=True)
            for family in (socket.AF_INET, socket.AF_INET6)
        ]
        for thread in threads:
            thread.start()

        deadline = time.monotonic() + DNS_TIMEOUT_SECONDS
        for thread in threads:
            thread.join(max(0, deadline - time.monotonic()))

        addresses = []
        errors = []
        timed_out = False
        while not results.empty():
            _, family_addresses, error = results.get_nowait()
            addresses.extend(family_addresses)
            if error is not None:
                errors.append(error)
        if any(thread.is_alive() for thread in threads):
            timed_out = True
        return addresses, errors, timed_out

    @staticmethod
    def _tcp_connect(addresses, port):
        deadline = time.monotonic() + TCP_TIMEOUT_SECONDS
        errors = []
        for family, socktype, protocol, _, address in addresses:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, "5-second TCP connection timeout"
            target = (address[0], port) if family == socket.AF_INET else (
                address[0],
                port,
                address[2],
                address[3],
            )
            try:
                with socket.socket(family, socktype, protocol) as connection:
                    connection.settimeout(remaining)
                    connection.connect(target)
                return ("IPv4" if family == socket.AF_INET else "IPv6"), None
            except OSError as error:
                errors.append(error)
        return None, str(errors[-1]) if errors else "no address was available"

    @staticmethod
    def _diagnosis(error, tcp_result, ipv4, ipv6, dns_failed=False, dns_timed_out=False):
        message = str(error).lower()
        sqlstate = getattr(error, "sqlstate", None)
        if dns_failed:
            if dns_timed_out:
                return (
                    "DNS did not resolve within the 5-second lookup deadline.",
                    "Verify the host and project status in Supabase; retry from "
                    "another DNS/network path if the project is active.",
                )
            return (
                "DNS returned no usable A or AAAA record for the configured host.",
                "Verify the host in the Supabase dashboard and confirm the project "
                "is active; if correct, check the local DNS/network.",
            )
        if "paused" in message:
            return (
                "Supabase reports that the project is paused.",
                "Restore/resume the project in the Supabase dashboard, then retry.",
            )
        if sqlstate == "28P01" or "password authentication failed" in message:
            return (
                "PostgreSQL rejected the credentials.",
                "Verify the current database password and username in Supabase; "
                "rotate any credential that has been exposed.",
            )
        if "ssl" in message or "certificate" in message:
            return (
                "The TLS/SSL handshake failed.",
                "Keep sslmode=require and check the Supabase connection settings "
                "and local TLS interception/VPN.",
            )
        if "refused" in message:
            return (
                "The host was reachable but refused the PostgreSQL connection.",
                "Confirm the project is active and the host/port are correct; "
                "consider the Supabase Session pooler on port 5432.",
            )
        if "timeout" in message or isinstance(error, psycopg.errors.ConnectionTimeout):
            if ipv6 and not ipv4:
                return (
                    "The IPv6-only database endpoint timed out.",
                    "Use the Supabase Session pooler on port 5432 with its "
                    "postgres.<project-ref> username.",
                )
            if tcp_result:
                return (
                    "TCP connected, but PostgreSQL did not complete its "
                    "connection/SSL handshake before the timeout.",
                    "Check whether the Supabase project is paused and verify the "
                    "database URL; if using the direct endpoint, try the Session "
                    "pooler on port 5432.",
                )
            return (
                "The PostgreSQL connection timed out.",
                "Check the Supabase project status and database URL, then retry "
                "from another network. Use the Session pooler if the direct "
                "endpoint is IPv6-only or inaccessible.",
            )
        if "tenant or user not found" in message:
            return (
                "The Supabase pooler did not recognize the project/user.",
                "Use the Session pooler connection details verbatim, including "
                "the postgres.<project-ref> username.",
            )
        if tcp_result is None and "refused" in (message or "").lower():
            return (
                "The TCP connection was refused.",
                "Confirm the host, port, project status, and network firewall.",
            )
        return (
            f"PostgreSQL returned {error.__class__.__name__}"
            + (f" (SQLSTATE {sqlstate})." if sqlstate else "."),
            "Review the Supabase connection details and the error above; do not "
            "change migrations or database data until connectivity is resolved.",
        )

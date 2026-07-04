#!/usr/bin/env python3
"""Wake a device on your home network through a FritzBox.

Connects to a FRITZ!Box over the TR-064 interface, lists the known network
devices and lets you pick one to wake up using Wake-on-LAN. Works locally
on your LAN or remotely via myFritz.

Connection settings are taken from (in order of precedence):
  1. command line arguments
  2. environment variables  (FRITZ_ADDRESS, FRITZ_PORT, FRITZ_USER,
     FRITZ_PASSWORD, FRITZ_TLS)
  3. interactive prompts

Local access uses a plain connection, e.g. `--address fritz.box --no-tls`.
For remote access through myFritz use the myfritz address, e.g.
    xxxxxxxxxxxxxxxx.myfritz.net
together with TLS (the default) and the HTTPS port configured in
"Internet > MyFRITZ! Account / Permit Access" (often 443).
"""

from __future__ import annotations

import argparse
import sys
from getpass import getpass

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import FritzConnectionException
from fritzconnection.lib.fritzhosts import FritzHosts
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console
from rich.table import Table

console = Console()


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #
class FritzSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRITZ_")

    address: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    tls: bool = True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List FritzBox network devices and wake one via Wake-on-LAN.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-a", "--address",
        help="FritzBox address or myfritz hostname (env: FRITZ_ADDRESS).",
    )
    parser.add_argument(
        "-p", "--port", type=int,
        help="TR-064 port. Defaults to 49443 with TLS, 49000 without "
             "(env: FRITZ_PORT).",
    )
    parser.add_argument(
        "-u", "--user",
        help="FritzBox user name (env: FRITZ_USER).",
    )
    parser.add_argument(
        "--password",
        help="FritzBox password (env: FRITZ_PASSWORD). Prompted if omitted.",
    )
    parser.add_argument(
        "--tls", action=argparse.BooleanOptionalAction, default=None,
        help="Use an encrypted TLS connection (default: on, required for "
             "myFritz). Pass --no-tls for a plain local connection "
             "(env: FRITZ_TLS).",
    )
    parser.add_argument(
        "--mac",
        help="Skip the menu and wake this MAC address directly.",
    )
    parser.add_argument(
        "-l", "--list", action="store_true",
        help="Only list devices, do not wake anything.",
    )
    parser.add_argument(
        "--offline-only", action="store_true",
        help="Show only offline devices (the usual Wake-on-LAN candidates).",
    )
    return parser.parse_args(argv)


def resolve_config(args: argparse.Namespace) -> FritzSettings:
    overrides = {
        "address": args.address,
        "port": args.port,
        "user": args.user,
        "password": args.password,
        "tls": args.tls,
    }
    settings = FritzSettings(**{k: v for k, v in overrides.items() if v is not None})

    if not settings.address:
        settings.address = input("FritzBox / myFritz address: ").strip()
    if not settings.address:
        sys.exit("No address given.")

    if settings.port is None:
        settings.port = 49443 if settings.tls else 49000

    if not settings.user:
        settings.user = input("User name: ").strip() or None

    if not settings.password:
        settings.password = getpass("Password: ")

    return settings


# --------------------------------------------------------------------------- #
# fritzbox interaction
# --------------------------------------------------------------------------- #
def connect(config: FritzSettings) -> FritzConnection:
    print(
        f"Connecting to {config.address}:{config.port} "
        f"({'TLS' if config.tls else 'plain'}) ...",
        flush=True,
    )
    return FritzConnection(
        address=config.address,
        port=config.port,
        user=config.user,
        password=config.password,
        use_tls=config.tls,
    )


def list_hosts(fc: FritzConnection, offline_only: bool = False) -> list[dict]:
    hosts = FritzHosts(fc).get_hosts_info()
    if offline_only:
        hosts = [h for h in hosts if not h.get("status")]
    # Sort offline first (wake candidates), then by name.
    hosts.sort(key=lambda h: (bool(h.get("status")), (h.get("name") or "").lower()))
    return hosts


def print_hosts(hosts: list[dict]) -> None:
    if not hosts:
        console.print("No devices found.")
        return
    table = Table(title="FritzBox network devices", title_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", no_wrap=True)
    table.add_column("IP", style="cyan")
    table.add_column("MAC", style="magenta")
    table.add_column("Status")
    for i, h in enumerate(hosts, start=1):
        online = bool(h.get("status"))
        status = "[green]● online[/green]" if online else "[dim]○ offline[/dim]"
        table.add_row(
            str(i),
            h.get("name") or "<unknown>",
            h.get("ip") or "",
            h.get("mac") or "",
            status,
        )
    console.print()
    console.print(table)
    console.print()


def wake(fc: FritzConnection, mac: str) -> None:
    fc.call_action(
        "Hosts1", "X_AVM-DE_WakeOnLANByMACAddress", NewMACAddress=mac
    )


# --------------------------------------------------------------------------- #
# interactive selection
# --------------------------------------------------------------------------- #
def choose_host(hosts: list[dict]) -> dict | None:
    while True:
        choice = input("Select device number to wake (q to quit): ").strip()
        if choice.lower() in {"q", "quit", "exit", ""}:
            return None
        if not choice.isdigit() or not (1 <= int(choice) <= len(hosts)):
            print(f"Please enter a number between 1 and {len(hosts)}.")
            continue
        return hosts[int(choice) - 1]


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = resolve_config(args)

    try:
        fc = connect(config)
    except FritzConnectionException as exc:
        print(f"Could not connect: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface anything else cleanly
        print(f"Connection failed: {exc}", file=sys.stderr)
        return 2

    # Direct wake by MAC, no menu.
    if args.mac:
        try:
            wake(fc, args.mac)
        except FritzConnectionException as exc:
            print(f"Wake-on-LAN failed: {exc}", file=sys.stderr)
            return 2
        print(f"Sent Wake-on-LAN packet to {args.mac}.")
        return 0

    try:
        hosts = list_hosts(fc, offline_only=args.offline_only)
    except FritzConnectionException as exc:
        print(f"Could not read device list: {exc}", file=sys.stderr)
        return 2

    print_hosts(hosts)

    if args.list or not hosts:
        return 0

    host = choose_host(hosts)
    if host is None:
        print("Nothing to do.")
        return 0

    mac = host.get("mac")
    name = host.get("name") or mac
    if not mac:
        print("Selected device has no MAC address; cannot wake it.", file=sys.stderr)
        return 1

    try:
        wake(fc, mac)
    except FritzConnectionException as exc:
        print(f"Wake-on-LAN failed: {exc}", file=sys.stderr)
        return 2

    print(f"Sent Wake-on-LAN packet to {name} ({mac}).")
    return 0


def cli() -> None:
    """Console-script entry point (see ``[project.scripts]`` in pyproject)."""
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    cli()

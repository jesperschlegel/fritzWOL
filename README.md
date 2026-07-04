# fritzWOL

A small text-based tool that connects to a **FRITZ!Box** — on your local
network or remotely through **myFritz** — lists the devices on your network and
lets you pick one to turn on via **Wake-on-LAN**.

It talks to the router over AVM's TR-064 interface using
[`fritzconnection`](https://github.com/kbr/fritzconnection).

```text
                       FritzBox network devices
┏━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ # ┃ Name           ┃ IP             ┃ MAC               ┃ Status    ┃
┡━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 1 │ Gaming-PC      │ 192.168.178.42 │ 1C:1B:0D:AA:BB:CC │ ○ offline │
│ 2 │ NAS            │ 192.168.178.20 │ 00:11:22:33:44:55 │ ○ offline │
│ 3 │ fritz.box      │ 192.168.178.1  │ 34:31:C4:AA:BB:CC │ ● online  │
│ 4 │ Living-Room-TV │ 192.168.178.60 │ B8:27:EB:11:22:33 │ ● online  │
│ 5 │ Office-Laptop  │ 192.168.178.31 │ 3C:22:FB:44:55:66 │ ● online  │
└───┴────────────────┴────────────────┴───────────────────┴───────────┘

Select device number to wake (q to quit):
```

## Requirements

- Python 3.12+.
- A FRITZ!Box user with the *"FRITZ!Box Settings"* permission.
- The target device must support **Wake-on-LAN** and have it enabled in its
  own network adapter / BIOS-UEFI settings, and be known to the FritzBox
  (it appears under `Home Network > Network`).
- For remote access: an active **myFritz** account and enabled internet access
  (`Internet > MyFRITZ! Account`).

## Install

Install it from PyPI:

```sh
pip install fritzwol         # or: uv tool install fritzwol / pipx install fritzwol
```

This puts a `fritzwol` command on your `PATH`. To install straight from GitHub
without cloning first:

```sh
uv tool install git+https://github.com/jesperschlegel/fritzWOL.git
```

Or from a local checkout:

```sh
uv tool install .          # or: pipx install .
```

For local development instead of a global install:

```sh
uv sync
uv run fritzwol            # or: uv run fritzwol.py
```

## Usage

Interactive (you will be prompted for anything not supplied):

```sh
fritzwol
```

It prints the known devices (offline ones first, as the usual wake candidates) and lets you pick one by number.

Remote access through myFritz — pass the HTTPS remote-access port your
FRITZ!Box exposes (`Internet > Permit Access > FRITZ!Box Services`, often 443
or a custom port):

```sh
fritzwol --address xxxxxxxxxxxxxxxx.myfritz.net --user myuser --port 443
```

> The default port (**49443**, the LAN TLS port) only applies to local access.
> For remote myFritz access you normally need to set `--port` to the HTTPS
> port configured on the box.

Local access on your home network:

```sh
fritzwol --address fritz.box --no-tls --user myuser
```

Just list devices without waking anything:

```sh
fritzwol --list
```

Show only offline devices (the usual wake candidates):

```sh
fritzwol --offline-only
```

Wake a specific MAC address directly (no menu):

```sh
fritzwol --mac 00:11:22:33:44:55
```

### Configuration via environment variables

Instead of flags you can set:

| Variable         | Meaning                                   |
| ---------------- | ----------------------------------------- |
| `FRITZ_ADDRESS`  | FritzBox address or myfritz hostname      |
| `FRITZ_PORT`     | TR-064 port (default 49443 TLS / 49000 not) |
| `FRITZ_USER`     | FritzBox user name                        |
| `FRITZ_PASSWORD` | FritzBox password                         |
| `FRITZ_TLS`      | `true`/`false` — use TLS (default `true`) |

The password is prompted for securely if it is not provided.

## How it works

1. Connects with `fritzconnection` (`use_tls=True` for myFritz).
2. Reads the host list via the `Hosts` TR-064 service (`get_hosts_info`).
3. Sends `X_AVM-DE_WakeOnLANByMACAddress` for the chosen device's MAC.

A woken device may take a moment to appear as *online*.

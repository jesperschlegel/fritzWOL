# fritzWOL

A small text-based tool that connects to a **FRITZ!Box** — on your local
network or remotely through **myFritz** — lists the devices on your network and
lets you pick one to turn on via **Wake-on-LAN**.

It talks to the router over AVM's TR-064 interface using
[`fritzconnection`](https://github.com/kbr/fritzconnection).

## Requirements

- [uv](https://docs.astral.sh/uv/)
- A FRITZ!Box user with the *"FRITZ!Box Settings"* permission.
- The target device must support **Wake-on-LAN** and have it enabled in its
  own network adapter / BIOS-UEFI settings, and be known to the FritzBox
  (it appears under `Home Network > Network`).
- For remote access: an active **myFritz** account and enabled internet access
  (`Internet > MyFRITZ! Account`).

> The per-device **"Auto Wake"** option (*"Automatically wake up ... when it is
> accessed from the internet"*) is **not** required. That setting only triggers
> a wake automatically on inbound internet traffic; this tool instead sends a
> wake packet on demand via the same mechanism as the device's *"Start
> Computer"* button (`X_AVM-DE_WakeOnLANByMACAddress`).

## Install

Install it as a command you can run from anywhere:

```sh
uv tool install .          # or: pipx install .
```

This puts a `fritzwol` command on your `PATH`. To install straight from GitHub
without cloning first:

```sh
uv tool install git+https://github.com/jesperschlegel/fritzWOL.git
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

Remote access through myFritz (TLS on, port 49443 are the defaults):

```sh
fritzwol --address xxxxxxxxxxxxxxxx.myfritz.net --user myuser
```

> The TR-064 interface uses port **49443** over TLS (not the myFritz web-UI
> port 443). This is the default, so you normally don't need `--port`.

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

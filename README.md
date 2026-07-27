# Edge Infrastructure Platform (EIP)

Network management software for private infrastructure. One device runs the control plane, everything else is managed from there.

Three-node mesh. Web control surface. Redundant storage. Automated operations. No Docker, no Kubernetes, no Nginx — just the fundamentals, kept lean.

---

## What It Is

EIP manages devices on a private network from a single control plane. Wake machines, check status, push backups — all from one interface over an encrypted mesh.

It runs on commodity hardware. The control plane is a Raspberry Pi drawing 5 watts. The compute node sleeps until it's needed. Nothing runs that doesn't have to.

## Current V1

This repository now contains the runnable control-plane service for the EIP V1 slice:

- `GET /health` — service health and registered app metadata
- `GET /eip/api/status/hub` — TCP probe for the Hub RDP endpoint
- `POST /eip/wake` — execute the configured Wake-on-LAN command
- operator dashboard at `/eip/`
- allowlisted action endpoints for local operator scripts
- systemd unit template for Raspberry Pi deployment
- tests for the Flask app, status probe route, and wake command wiring

Smart Mirror and other dashboard modules are separate projects. EIP V1 stays focused on private infrastructure control.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tailscale Mesh (WireGuard)           │
│                    Trust boundary for all traffic       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Pi (Edge)   │  │ Hub (Compute)│  │    Laptop    │   │
│  │  Always-on   │  │  On-demand   │  │  (Operator)  │   │
│  │ Control plane│  │ Wakes via WoL│  │              │   │
│  │              │  │              │  │              │   │
│  │  Flask API   │  │  RAID1 (4TB) │  │  Scripts/    │   │
│  │  systemd svc │  │  SMB shares  │  │  Scheduled   │   │
│  │  Status mon. │  │  RDP target  │  │  backups     │   │
│  │  WoL dispatch│  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│   tailnet: edge     tailnet: hub       tailnet: laptop   │
└─────────────────────────────────────────────────────────┘
              Private LAN · Tailscale + MagicDNS
```

**Pi** — Always on. Runs the Flask API, systemd service, status monitoring, WoL dispatch. 5W idle.

**Hub** — Sleeps by default. RAID1 storage (4TB mirrored CMR), SMB shares, RDP target. Wakes on demand.

**Laptop** — Operator. Runs scheduled backups and on-demand scripts. All scripts source a shared config file.

---

## Design Decisions

### Tailscale as trust boundary

All traffic runs over the Tailscale mesh. No ports exposed to the internet. No firewall rules to maintain. No reverse proxy. No cert renewal.

The alternative is Nginx/Caddy with Let's Encrypt and manual firewall management. That's a lot of surface area to maintain for a private network. Tailscale reduces the security question to one thing: is this device in the mesh or not.

Services aren't publicly accessible. That's intentional. Public exposure is a separate problem for later.

### No containers

Flask runs directly under systemd on the Pi. No Docker, no container runtime.

Containers add a runtime, image storage, and network bridging. On a Pi, that overhead matters. More importantly, none of the problems containers solve — dependency isolation, reproducible deploys, horizontal scaling — exist here yet. Each node has one job.

This changes when multi-service orchestration on a single node becomes necessary. The architecture doesn't prevent it.

### Wake-on-LAN over always-on compute

The Hub draws 80-150W under load. Running that 24/7 for occasional use is wasteful. The Pi sends a WoL packet, the Hub is up in ~15 seconds, and it goes back to sleep when it's done.

The Flask API exposes `/wake`. Automation scripts call it, poll `/api/status/hub` until the Hub responds, then proceed. Wake, wait, act. Every Hub-dependent operation follows this pattern.

### RAID1 with CMR drives

Two 4TB CMR drives in mirror. Lose one, the other has a complete copy.

CMR over SMR because SMR write performance degrades unpredictably during rebuilds — which is the worst time for unpredictable performance. 4TB usable from 8TB raw. The tradeoff is capacity for simplicity and reliability.

### Shared config pattern

Every script on the laptop sources `eip_config.bat` — one file with all connection details (hosts, IPs, paths, credentials). Without it, updating a single Tailscale IP means editing every script. With it, one file is the source of truth.

Scripts:
- `eip_config.bat` — shared state
- `wake_and_rdp.bat` — wake Hub, launch Remote Desktop
- `wake_and_backup.bat` — wake Hub, robocopy Obsidian vault to RAID1

### Automated nightly backup

Midnight. Robocopy mirror mode — only deltas transfer. Script wakes the Hub via Pi, waits for it to come online, runs the backup. Scheduled via `schtasks`. No human required.

---

## Stack

| Layer | Tool | Reason |
|-------|------|--------|
| Network | Tailscale (WireGuard) | Encrypted mesh, no exposed ports |
| Control plane | Flask | Small API/UI surface, easy Pi deployment |
| Process mgmt | systemd | OS-native lifecycle management |
| Monitoring | Python TCP probe | No agent required on targets |
| Storage | RAID1 / mdadm / SMB | Mirror redundancy, network-accessible |
| Remote access | RDP over Tailscale | Native protocol, encrypted transport |
| Automation | Batch + schtasks | OS-native, no dependencies |
| WoL | Configured local command | Keeps packet dispatch swappable |

---

## Repository Structure

```text
server.py                 Flask app factory and process entry point
apps/eip/                 Dashboard, Wake/status Blueprint, action registry
tests/                    Unit tests for the V1 control plane
.env.example              Example runtime configuration
eip-platform.service      systemd unit template for Pi deployment
docs/                     Design notes and versioned architecture docs
```

---

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Create local config:

```bash
cp .env.example .env
```

Update `.env` for the actual hub host, port, timeout, and Wake-on-LAN command.

Run locally:

```bash
python server.py
```

Then open:

```text
http://127.0.0.1:5000/health
http://127.0.0.1:5000/eip/
http://127.0.0.1:5000/eip/api/status/hub
```

---

## Configuration

| Variable | Purpose | Example |
|----------|---------|---------|
| `EIP_HOST` | Flask bind host | `0.0.0.0` |
| `EIP_PORT` | Flask bind port | `5000` |
| `EIP_DEBUG` | Enable Flask debug mode | `false` |
| `EIP_HUB_HOST` | Hub hostname or Tailscale MagicDNS name | `hub.tailnet.ts.net` |
| `EIP_HUB_PORT` | Hub status probe port | `3389` |
| `EIP_STATUS_TIMEOUT` | TCP probe timeout in seconds | `2` |
| `EIP_WAKE_COMMAND` | Local command used to wake the Hub | `wakepc hub` |
| `EIP_RDP_HOST` | Host passed to `mstsc.exe` from the dashboard | `hub` |
| `EIP_WAKE_RDP_SCRIPT` | Optional Windows script path for the Wake + RDP button | `C:\Users\you\Scripts\wake_and_rdp.bat` |
| `EIP_WAKE_BACKUP_SCRIPT` | Optional Windows script path for the Wake + Backup button | `C:\Users\you\Scripts\wake_and_backup.bat` |

Secrets and machine-specific values belong in `.env`, never in committed files.

---

## API

| Endpoint | Method | What it does |
|----------|--------|--------------|
| `/health` | GET | Service health and registered app metadata |
| `/eip/api/status/hub` | GET | TCP probe — is the Hub online |
| `/eip/api/actions` | GET | Dashboard action metadata |
| `/eip/api/actions/<action_id>` | POST | Run an allowlisted dashboard action |
| `/eip/wake` | POST | Execute the configured Wake-on-LAN command |

Example status response:

```json
{
  "target": "hub",
  "host": "hub.tailnet.ts.net",
  "port": 3389,
  "status": "ONLINE",
  "timestamp": "2026-05-17T16:00:00+00:00"
}
```

---

## Testing

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

The tests mock network probes and wake-command execution. They verify the app wiring and command boundaries without sending real magic packets.

---

## Raspberry Pi Deployment

One intended deployment shape is `/opt/eip` on the Pi:

```bash
sudo mkdir -p /opt/eip
sudo cp -r . /opt/eip
cd /opt/eip
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
sudo cp eip-platform.service /etc/systemd/system/eip-platform.service
sudo systemctl daemon-reload
sudo systemctl enable --now eip-platform
```

Adjust `eip-platform.service` and `.env` for the actual deployment path and wake command.

---

## Status

**Phase 1 (now):** Working V1 control plane: hub status, wake action, health endpoint, systemd template, tests, and documented architecture.

**Phase 2:** Modularize. Reproducible architecture, swappable components, declarative config.

**Phase 3:** Downloadable app. Install on one device, manage everything from there.

---

## What's Not Here

No containers — [by design](#no-containers). No public endpoints — the mesh is the boundary. No Prometheus — three nodes don't need a monitoring stack. No Smart Mirror code — that is a separate project.

---

## License

MIT

# Edge Infrastructure Platform (EIP)

Network management software for private infrastructure. One device runs the control plane, everything else is managed from there.

Three-node mesh. Web control surface. Redundant storage. Automated operations. No Docker, no Kubernetes, no Nginx — just the fundamentals, kept lean.

---

## What It Is

EIP manages devices on a private network from a single control plane. Wake machines, check status, push backups — all from one interface over an encrypted mesh.

It runs on commodity hardware. The control plane is a Raspberry Pi drawing 5 watts. The compute node sleeps until it's needed. Nothing runs that doesn't have to.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Tailscale Mesh (WireGuard)             │
│                   Trust boundary for all traffic         │
│                                                          │
│  ┌──────────────-┐  ┌─────────────-─┐  ┌──────────────┐  │
│  │  Pi (Edge)    │  │  Hub (Compute)│  │   Laptop     │  │
│  │  Always-on    │  │  On-demand    │  │  (Operator)  │  │
│  │  Control plane│  │  Wakes via WoL│  │              │  │
│  │               │  │               │  │              │  │
│  │  Flask API    │  │  RAID1 (4TB)  │  │  Scripts/    │  │
│  │  systemd svc  │  │  SMB shares   │  │  Scheduled   │  │
│  │  Status mon.  │  │  RDP target   │  │  backups     │  │
│  │  WoL dispatch │  │               │  │              │  │
│  └──────────────┘   └──────────────┘   └──────────────┘  │
│   100.66.29.15       100.112.94.2       100.67.141.87    │
└─────────────────────────────────────────────────────────┘
         LAN: 192.168.4.0/24 · Tailscale + MagicDNS
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
| Control plane | Flask | Single-file API, minimal |
| Process mgmt | systemd | OS-native lifecycle management |
| Monitoring | `nc -z` | TCP probe, no agent on targets |
| Storage | RAID1 / mdadm / SMB | Mirror redundancy, network-accessible |
| Remote access | RDP over Tailscale | Native protocol, encrypted transport |
| Automation | Batch + schtasks | OS-native, no dependencies |
| WoL | Python + wakeonlan | Two lines of code |

---

## API

| Endpoint | Method | What it does |
|----------|--------|--------------|
| `/api/status/hub` | GET | TCP probe — is the Hub online |
| `/wake` | POST | Send WoL magic packet to Hub |

---

## Status

**Phase 1 (now):** Working system, documented decisions. Portfolio state.

**Phase 2:** Modularize. Reproducible architecture, swappable components, declarative config.

**Phase 3:** Downloadable app. Install on one device, manage everything from there.

---

## What's Not Here

No containers — [by design](#no-containers). No public endpoints — the mesh is the boundary. No CI/CD — deploy target is one Pi, `scp` and `systemctl restart` is the process. No Prometheus — three nodes don't need a monitoring stack.

---

## License

MIT

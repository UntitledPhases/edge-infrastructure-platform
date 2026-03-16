# Edge Infrastructure Platform (EIP)

Open-source network management software. Install on one device, manage your network from there.

EIP is a working multi-node infrastructure with a web control surface, built fundamentals-first — no Docker, no Kubernetes, no Nginx. The design principle is resource discipline: minimum overhead, maximum capability per watt, per dollar, per line of code. Every architectural decision is grounded in the CIA triad (confidentiality, integrity, availability) as engineering discipline, not marketing language.

**Current state:** Three-node mesh network with centralized control plane, automated operations, and redundant storage. Phase 1 is a documented, working system with defensible design rationale.

---

## Why This Exists

Most homelab projects skip straight to orchestration tooling — Docker Compose files, Ansible playbooks, Terraform configs — without understanding what those tools abstract away. EIP goes the other direction: build the fundamentals by hand, understand exactly what each layer does, then decide what's worth abstracting.

But this isn't just an exercise in learning primitives. The deeper constraint is resource discipline — getting the most out of every component by understanding what it actually needs to do and refusing to over-provision. A 5W Pi running the control plane instead of a full server. On-demand compute that sleeps when idle. Delta-only backups over network mounts. No tool introduced until the problem it solves actually exists. The goal is a system where nothing is wasted and everything is justified.

The long-term vision is a downloadable application: install it on one device and that device becomes your network control plane. Today it's the working foundation for that.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Tailscale Mesh (WireGuard)             │
│                   Trust boundary for all traffic         │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Pi (Edge)   │  │  Hub (Compute)│  │   Laptop     │  │
│  │  Always-on    │  │  On-demand    │  │  (Operator)  │  │
│  │  Control plane│  │  Wakes via WoL│  │              │  │
│  │              │  │              │  │              │  │
│  │  Flask API    │  │  RAID1 (4TB) │  │  Scripts/    │  │
│  │  systemd svc  │  │  SMB shares  │  │  Scheduled   │  │
│  │  Status mon.  │  │  RDP target  │  │  backups     │  │
│  │  WoL dispatch │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│   100.66.29.15      100.112.94.2      100.67.141.87     │
└─────────────────────────────────────────────────────────┘
         LAN: 192.168.4.0/24 · Tailscale + MagicDNS
```

Three nodes, each with a clear role:

- **Pi (rasplient)** — Always-on edge node running the control plane. Draws ~5W, stays up 24/7. Runs Flask API, systemd service, status monitoring, and Wake-on-LAN dispatch.
- **Hub** — Compute node with RAID1 storage. Sleeps until needed, wakes on demand via WoL. Hosts redundant storage (4TB mirrored CMR drives) and serves as RDP target for remote work.
- **Laptop** — Operator workstation. Runs scheduled backup scripts and on-demand commands. All automation scripts follow a shared-config pattern for consistency.

---

## Design Decisions

This is the section that matters. Every choice below optimizes for the same thing: maximum capability from minimum resources, with every layer understood and justified.

### Tailscale as trust boundary — not just convenience

**Decision:** All inter-node communication runs over Tailscale's WireGuard mesh. No ports exposed to the public internet. No firewall rules to maintain.

**Why:** The conventional homelab approach is to expose services via reverse proxy (Nginx/Caddy) with Let's Encrypt certs and firewall rules. That creates a large attack surface that requires ongoing maintenance — certificate renewal, firewall auditing, port management. Tailscale collapses this to a single trust decision: is this device in the mesh? If yes, it can communicate. If no, it can't. The network boundary *is* the security boundary.

**Tradeoff acknowledged:** This means EIP services aren't publicly accessible. That's intentional for Phase 1 — the control plane manages a private network, not a public one. Public exposure is a Phase 2+ concern and will be handled as a deliberate extension, not a default.

### No containers, no orchestration — fundamentals first

**Decision:** Flask runs directly on the Pi under systemd. No Docker, no container runtime, no orchestrator.

**Why:** Containers solve real problems — dependency isolation, reproducible deploys, horizontal scaling. None of those problems exist yet in a three-node network where each node has a single role. Introducing Docker here would add a layer of abstraction that hides the actual operating system mechanics: process management, service lifecycle, networking, file permissions. It would also add resource overhead — a container runtime, image storage, network bridging — on a Pi where every megabyte of RAM matters. Understanding the mechanics *and* keeping the system lean are the same goal here.

**When this changes:** When EIP needs multi-service orchestration on a single node, or when deployment reproducibility becomes a bottleneck. The architecture is designed so containerization is an additive change, not a rewrite.

### Wake-on-LAN over always-on compute

**Decision:** The Hub sleeps by default and wakes on demand via WoL packets dispatched from the Pi.

**Why:** A desktop-class machine drawing 80-150W 24/7 to serve occasional compute and storage requests is wasteful and shortens hardware life. WoL lets the Pi (5W, always-on) act as the gatekeeper. The Hub is available in ~15 seconds when needed and consuming zero power when it's not.

**Implementation:** The Pi's Flask API exposes a `/wake` endpoint. The laptop's automation scripts call this endpoint, then poll the Hub's status until it's online before proceeding. This pattern — wake, wait, act — is reused across all Hub-dependent operations.

### RAID1 with CMR drives — integrity over capacity

**Decision:** Hub storage is two 4TB CMR (Conventional Magnetic Recording) drives in RAID1 (mirror).

**Why:** RAID1 was chosen over RAID5/RAID0 because the failure mode is simple and recoverable — lose one drive, the other has a complete copy. CMR drives were chosen over SMR (Shingled Magnetic Recording) because SMR drives have unpredictable write performance during RAID rebuilds, which is exactly when you need predictable performance most. The capacity tradeoff (4TB usable from 8TB raw) is acceptable because the use case is critical data redundancy, not bulk storage.

### Shared-config script pattern

**Decision:** All automation scripts on the laptop source a single `eip_config.bat` file for shared state (hostnames, IP addresses, credentials, paths).

**Why:** Without this, every script hardcodes its own copy of connection details. That means updating a Tailscale IP requires editing every script individually — a maintenance burden that scales linearly with the number of scripts. The shared-config pattern means one file is the source of truth. Each script is a function that calls it.

**Scripts:**
- `eip_config.bat` — shared configuration (PI_USER, PI_HOST, WAKE_CMD, RDP_HOST, etc.)
- `wake_and_rdp.bat` — wakes Hub + launches Remote Desktop
- `wake_and_backup.bat` — wakes Hub + runs robocopy mirror of Obsidian vault to RAID1

### Automated backup via scheduled task

**Decision:** Nightly midnight backup of Obsidian vault from laptop to Hub's RAID1 storage, scheduled via `schtasks`.

**Why:** Manual backups don't happen. The backup runs robocopy in mirror mode over the network mount, which means it only transfers changes — fast, incremental, and idempotent. The script handles the full lifecycle: wake the Hub (via Pi), wait for it to come online, run the backup, done. No human in the loop.

---

## Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Mesh network | Tailscale (WireGuard) | Encrypted overlay, zero-config DNS, no exposed ports |
| Control plane | Flask + Python | Lightweight, single-file API, no framework overhead |
| Process management | systemd | OS-native, handles restart/logging/dependencies |
| Status monitoring | `nc -z` (netcat) | Minimal — TCP port check, no agent required on targets |
| Storage | RAID1, mdadm, SMB | Mirror redundancy, standard Linux tooling, network-accessible |
| Remote access | RDP + Tailscale | Native Windows protocol over encrypted mesh |
| Automation | Batch scripts + schtasks | Native Windows scheduling, no external dependencies |
| Wake-on-LAN | Python + `wakeonlan` | Two-line implementation, dispatched from Pi |

---

## API

The Pi exposes a minimal Flask API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status/hub` | GET | Returns Hub online/offline status via TCP probe |
| `/wake` | POST | Sends WoL magic packet to Hub |

The web UI at the Pi's address provides a control panel for status monitoring and wake operations.

---

## Project Status

**Phase 1 (current):** Working multi-node infrastructure with documented design rationale. This is the portfolio milestone — the system works, the decisions are defensible, the documentation tells the story.

**Phase 2 (planned):** Modularize — reproducible architecture, swappable components, declarative configuration.

**Phase 3 (vision):** Downloadable application — install on one device, manage your network from there.

---

## What's Not Here (Yet)

Transparency about scope is as important as what's built:

- **No container orchestration** — deliberate, not deferred. See [design decisions](#no-containers-no-orchestration--fundamentals-first).
- **No public service exposure** — the trust boundary is the mesh. Public-facing services are a Phase 2 concern.
- **No CI/CD** — the deployment target is a single Pi. `scp` and `systemctl restart` is the deploy process. CI/CD overhead isn't justified until there are multiple services or contributors.
- **No monitoring/alerting stack** — status checks are synchronous via the API. Prometheus/Grafana is overkill for three nodes. If the Pi is down, the control plane is down, and I'll know.

---

## License

MIT

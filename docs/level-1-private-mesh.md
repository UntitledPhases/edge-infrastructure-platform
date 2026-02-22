## Objective
-----------------------
Provide secure remote access to devices on a private residential LAN through a persistent edge gateway.
This stage enables the foundational connectivity and control layer upon which all subsequent infrastructure components are built.


## System Environment
-----------------------
The edge node is deployed on a Raspberry Pi running Raspberry Pi OS Lite.

This minimal, headless Linux distribution was selected to provide:
- low resource overhead
- stable long-term operation
- remote-only administration
- suitability for always-on infrastructure roles

The system is configured for continuous operation with no graphical interface and no attached peripherals after initial provisioning.


## Network Architecture
-----------------------
Connectivity is provided through a private mesh VPN implemented using Tailscale.
All participating devices join a shared VPN and communicate using identity based addressing provided by Tailscale.
No inbound ports are exposed on the local network or router, all communication is achieved through the VPN.


## Remote Access Configuration
-----------------------
Remote administrative access to the edge node is provided through SSH over the Tailscale mesh network.

The Raspberry Pi operates as a persistent node within the VPN and is reachable using both its assigned Tailscale IP address and MagicDNS hostname resolution.

Access characteristics:

- SSH service enabled on the Raspberry Pi
- Identity-based network access enforced through Tailscale authentication
- Hostname resolution via MagicDNS
- No dependency on local network addressing or router configuration
- No public-facing SSH exposure

This configuration enables secure remote management from any authenticated device joined to the tailnet without requiring port forwarding or direct LAN connectivity.


## System Validation
-----------------------
The following validation procedures were performed to confirm stable operation and persistent remote accessibility:

- Verified successful SSH connection over Tailscale from an external network
- Confirmed hostname resolution via MagicDNS
- Performed full system reboot and verified automatic startup of required services
- Confirmed tailscaled service initialization at boot
- Confirmed SSH service availability immediately after reboot
- Verified continued headless operation with no physical interaction required

All tests confirmed reliable remote access and persistent node availability.


## Result
-----------------------
The Raspberry Pi now functions as a stable, always-on edge gateway within a private mesh VPN.

Operational capabilities achieved:

- Secure remote administrative access from any authenticated device
- Persistent network presence independent of local LAN configuration
- Encrypted peer-to-peer connectivity without public exposure
- Fully headless infrastructure operation
- Reliable automatic recovery following reboot or power interruption

The node is now capable of serving as a remote control point for private network resources.


## Architectural Role
-----------------------
Level 1 establishes the foundational connectivity layer for the Edge Infrastructure Platform.

The persistent edge node provides the secure remote access and network presence required for all higher-level system capabilities, including public service exposure, device orchestration, and defensive monitoring.

All subsequent infrastructure components depend on the availability and stability of this layer.


## Next Stage
-----------------------
Level 2 extends the system from private mesh connectivity to controlled public exposure through a secure web-facing ingress point.

Planned additions include:

- SSH hardening and key-based authentication
- Reverse proxy deployment for service routing
- Raspberry Pi thin-client role (Plient) for workstation orchestration
- Wake-on-LAN integration for internal device control

# Ver. 1.0: Overview
A scalable solution for secure remote access & control of host devices on private networks. 


## Design Goals
Created as the foundation for a centralized smart home control center.
- private by default
- identity based access
- LAN first orchestration
- Low resource footprint
- Deterministic configuration
- Modular architecture

## Architecture
### Components
- Client Device (tailnet authenticated)
- Edge Node (Raspberry Pi)
    - Flask
    - Configuration
- LAN Network
- Hub Host

### Communication Flow
1. User connects to Pi over Tailscale.
2. Pi serves web UI.
3. Pi orchestrates over LAN.
4. Pi returns results to client

### Trust boundaries
EIP is private by default and only reachable from authenticated tailscale devices or through LAN. Currently, EIP exposes no public ingress from the internet. The web-based control panel binds only to the raspberry pi's tailscale interface, `100.66.29.15:5000`, so only requests originating from within the VPN network are accepted.

## Data Flow Diagram
```
Operator (Tailnet)
        |
        | HTTPS (Tailscale)
        v
[Control Plane on Pi] ---- LAN ----> [Windows Hub]
             |
             v
           [Logs]
```

## Use Cases

### UC-1: View Host Status
**Actor:** Authenticated Tailnet device  
**Trigger:** Operator opens control panel  
**System Behavior:** Performs LAN RDP port probe  
**Success Criteria:** Control panel accurately reflects host reachability  
**Failure Handling:** Control panel displays offline and remains responsive. System does not attempt to infer the power state. Failure is logged with timestamps.

### UC-2: Wake Host
**Actor:** Authenticated Tailnet Device  
**Trigger:** Operator clicks `Wake` button in Control Panel  
**System Behavior:** Broadcasts magic packet to network and waits for RDP port probe reply.
**Success Criteria:**  
**Failure Handling:**  
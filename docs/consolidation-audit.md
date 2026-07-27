# EIP Consolidation Audit

Date: 2026-06-17

## Repositories Reviewed

| Repository | Current role | Keep / move |
| --- | --- | --- |
| `UntitledPhases/edge-infrastructure-platform` | Current EIP control plane. Flask app, hub status probe, wake endpoint, systemd unit, tests, current README and architecture notes. | Use as canonical EIP backend. |
| `UntitledPhases/eip-platform` | Earlier universal Flask platform. Contains app auto-discovery plus the Smart Mirror backend bridge to Notion. | Treat as ancestor/reference. Salvage app-discovery and mirror backend only when EIP needs modules again. |
| `UntitledPhases/Smart-Mirror` | Svelte/Vite kiosk UI. Expects `/mirror/api/data` and has a Pi kiosk service script. | Keep separate frontend. Mount under EIP later only after the backend module is reintroduced. |

## Findings

- `edge-infrastructure-platform` is the cleanest source of truth for EIP V1.
- `eip-platform` has useful module boundaries, but it mixed EIP control and mirror concerns before the EIP control plane was hardened.
- `Smart-Mirror` is not a duplicate EIP dashboard. It is a separate ambient display surface.
- Local Windows scripts live in `%USERPROFILE%\Scripts`:
  - `eip_config.bat`
  - `wake_and_rdp.bat`
  - `wake_and_backup.bat`

## Decision

Use this local `EIP` folder as the working copy for `edge-infrastructure-platform`. Build the operator dashboard here first. Keep mirror work as a later module integration rather than merging it into the first dashboard pass.

## Immediate Dashboard Scope

- Hub status display.
- Wake Hub action.
- Open RDP action when running on Windows.
- Wake + RDP script button when `wake_and_rdp.bat` exists.
- Wake + Backup script button when `wake_and_backup.bat` exists.
- All button commands come from an allowlisted action registry, not user-supplied shell input.

## Later Consolidation

- Reintroduce app auto-discovery if multiple EIP apps become active again.
- Add `/mirror/` only after deciding whether the Pi should serve the Svelte production build or keep Smart Mirror as its own service.
- Add deployment docs for the split laptop/Pi model: laptop dashboard actions versus Pi-hosted control-plane actions.

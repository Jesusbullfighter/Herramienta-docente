---
name: dev-machine-hardware
description: "User's primary development laptop hardware, OS, and the 2026-08-30 HDD-to-SSD migration"
metadata: 
  node_type: memory
  type: user
  originSessionId: bb800091-dc80-460c-aca9-347b9c337178
  modified: 2026-08-30T16:31:40.493Z
---

User's primary development laptop is a Toshiba Satellite L755, running Ubuntu 24.04 LTS (Noble), username `jesus`. Claude Desktop/Code is installed via the `claude-desktop` apt package from a third-party repo (`pkg.claude-desktop-debian.dev`), not via npm.

On 2026-08-30, migrated the internal drive from a 596GB mechanical HDD (Toshiba MK6475GSX, using LVM) to a 250GB SSD via a **clean OS reinstall** (not a disk clone) — home folder (~70GB) was backed up externally first, verified to include dotfiles (`.claude`, `.claude.json`, `.config/Claude`, `.ssh`, `.gnupg`, `.mozilla`), then restored via a prepared script after the fresh Ubuntu install.

**How to apply:** the user also has a separate project directory, [[Optimización del ordenador]], dedicated to computer-optimization work — this hardware context (laptop model, disk size, OS) is directly relevant there. Relevant for any future troubleshooting or performance questions about this machine.

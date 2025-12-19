# 🛡️ Project Sentry: Autonomous Data Recovery & Sanitation Platform

> **"The Reaper for Digital Clutter."**
> A sovereign, air-gapped data consolidation system designed for IT consultants and sensitive data recovery operations.

![Version](https://img.shields.io/badge/version-2.0.0-neon.svg) ![Docker](https://img.shields.io/badge/deployment-docker-blue.svg) ![Platform](https://img.shields.io/badge/platform-RaspberryPi%20%7C%20Linux-red.svg)

---

## 📋 Mission Profile

Project Sentry is a specialized "Search and Destroy" engine for digital files. It solves a specific problem faced by IT consultants: **Consolidating fragmented data from multiple sources (Old HDDs, USBs, Network Shares) into a single "Golden Master" without creating duplicates.**

### ⚡ Key Capabilities
* **Omni-Source Scanning:** Simultaneously ingest data from Local USBs, Internal SATA/NVMe drives, and Network SMB Shares.
* **The Tree View:** A tactical file browser that allows granular selection of entire drives or specific sub-folders.
* **The Reaper Engine:** A hashing-based deduplication agent that identifies files by content (MD5), not just name.
* **Host Penetration:** Uses Docker Privilege Elevation to mount and scan the host operating system's entire filesystem.
* **Air-Gap Ready:** Fully self-contained. No cloud dependencies. No phone home.

---

## 🛠️ Deployment Protocols

### Option A: The "Field Kit" (Raspberry Pi 5)
*Ideal for on-site client data recovery.*

1.  **Clone:**
    ```bash
    git clone [https://github.com/ghazeltine/project-sentry.git](https://github.com/ghazeltine/project-sentry.git)
    cd project-sentry
    ```
2.  **Engage:**
    ```bash
    docker compose up -d --build
    ```
3.  **Access:** Connect via Ethernet/Wi-Fi and navigate to `http://<PI_IP>:8000`.

### Option B: The "Lab Bench" (Linux Workstation)
*Ideal for processing massive storage arrays.*

1.  Ensure Docker Engine is installed.
2.  Run the same commands as above.
3.  **Note:** Sentry mounts your host filesystem at `/host_fs` to allow scanning of internal drives.

---

## 🕹️ Operational Guide

### Phase 1: Connection
* **Physical:** Plug drives into the host. Sentry auto-detects mounts in `/media`, `/mnt`, and `/run/media`.
* **Network:** Use the **"Connect"** panel to mount SMB shares (NAS, Windows Server) directly into the Sentry filesystem.

### Phase 2: Selection (The Three Zones)
1.  **Source Selector (Middle):** Use the dropdown to jump between USBs, Network Mounts, or the Host OS.
2.  **Gold Master (Left):** Select folders containing data you want to **PROTECT**.
    * *Rule:* Files here are indexed but NEVER touched.
3.  **Targets (Right):** Select folders containing data you want to **CLEAN**.
    * *Rule:* If a file here exists in Gold, it will be marked for deletion.

### Phase 3: Execution
1.  **Start Scan:** The system indexes all selected paths (Green Status Bar).
2.  **Analyze:** The Reaper compares hashes between Gold and Target.
3.  **Execute:**
    * Click **"EXECUTE REAPER"** to permanently delete duplicates from the Target drives.
    * *Result:* Your Target drives now contain **only unique data** that was missing from your Master.

---

**Property of Sovereign Silicon**
*Internal Tooling - Authorized Use Only*

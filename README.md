# 🛡️ PROJECT SENTRY
### Autonomous Data Recovery & Deduplication Platform
**The "Gold Standard" for Digital Hygiene.**

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_5_%7C_Linux_%7C_Docker-red?style=for-the-badge&logo=raspberrypi)
![AI Chip](https://img.shields.io/badge/AI_Acceleration-Hailo--8L_NPU-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

---

## 📖 Overview
**Project Sentry** is an intelligent data management system designed to consolidate fractured digital archives spread across multiple physical drives. Unlike standard duplicate finders, Sentry operates on a strict **"Gold Master" Protocol**: it designates one drive as the immutable source of truth and surgically removes redundancy from target drives only when it is 100% safe to do so.

Built for the **Edge**, Sentry is optimized for the **Raspberry Pi 5 with Hailo-8L AI Kit**, utilizing a hybrid engine that combines cryptographic precision with semantic visual understanding.

---

## 🚀 Key Features

### 🔒 The "Gold Master" Protocol
* **Immutable Protection:** Files on the Master Drive are *read-only* to the system.
* **Surgical Strikes:** A file is only deleted from a Target Drive if an exact cryptographic match exists on the Master.
* **The "Kill List":** Users must explicitly authorize deletion after reviewing the database report.

### 🧠 Hybrid AI Engine (CPU + NPU)
Sentry uses a dual-layer scanning engine:
1.  **Cryptographic Layer (CPU):** Uses **BLAKE2b** hashing (faster and safer than MD5/SHA) to detect byte-for-byte duplicates.
2.  **Semantic Vision Layer (NPU):** Uses the **Hailo-8L AI Chip** to generate "Visual Vectors."
    * *Detects resized images, format changes (PNG vs JPG), and slight edits.*
    * *Falls back to CPU Perceptual Hashing (dHash) on non-AI hardware.*

### 👻 The Ghostbuster (Janitor)
* **Smart Cleanup:** After deleting files, the Janitor recursively scans directory trees bottom-up.
* **Void Removal:** Dissolves empty "Ghost Folders" to leave a clean, organized hierarchy.

### 🛡️ Hardware-Aware Logic
* **Cross-Platform Mounts:** Auto-detects and handles **Mac HFS+ (Journaled)** and **Windows NTFS** permissions.
* **Health Checks:** Monitors drive connectivity (`lsblk`) and prevents operations on "Dirty" or read-only file systems.

---

## 💻 Compatibility & Deployment

Project Sentry is built on **Python 3.11** and **FastAPI**, containerized with **Docker**.

### Supported Operating Systems
| OS | Support Level | Notes |
| :--- | :--- | :--- |
| **Raspberry Pi OS (64-bit)** | 🟢 **Tier 1 (Native)** | Full AI Acceleration via Hailo-8L. |
| **Ubuntu / Debian Linux** | 🟢 **Tier 1** | Native USB handling. CPU-based Visual Hashing. |
| **macOS / Windows** | 🟡 **Tier 2** | Works via Docker Desktop. Requires manual drive sharing. |

### Deployment Models

#### 1. The "Edge Sentry" (Recommended)
* **Hardware:** Raspberry Pi 5 + Hailo AI Kit + NVMe/USB Storage.
* **Orchestration:** Kubernetes (K3s) or Docker Compose.
* **Benefit:** Low power, high performance, always-on scanning.

#### 2. The "Laptop Lab"
* **Hardware:** Any standard laptop (x86/AMD64).
* **Mode:** CPU Fallback.
* **Benefit:** Portable, good for initial testing and organizing drives before archiving.

---

## ⚡ Quick Start

### Option A: Docker (Fastest)
```bash
# 1. Build the image
docker build -t project-sentry:v1 .

# 2. Run with USB access (Linux/Pi)
docker run -d \
  -p 8000:8000 \
  --privileged \
  -v /dev:/dev \
  -v /media:/media \
  project-sentry:v1

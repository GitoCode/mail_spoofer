<div align="center">

```
███████╗██████╗  ██████╗  ██████╗ ███████╗ ██████╗ ██╗   ██╗██╗
██╔════╝██╔══██╗██╔═══██╗██╔═══██╗██╔════╝██╔════╝ ██║   ██║██║
███████╗██████╔╝██║   ██║██║   ██║█████╗  ██║  ███╗██║   ██║██║
╚════██║██╔═══╝ ██║   ██║██║   ██║██╔══╝  ██║   ██║██║   ██║██║
███████║██║     ╚██████╔╝╚██████╔╝██║     ╚██████╔╝╚██████╔╝██║
╚══════╝╚═╝      ╚═════╝  ╚═════╝ ╚═╝      ╚═════╝  ╚═════╝ ╚═╝
```

**Email Spoofing Demo Tool — DEF CON Edition**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-7c3aed?style=flat-square)](LICENSE)
[![DEF CON](https://img.shields.io/badge/Presented%20at-DEF%20CON-ef4444?style=flat-square)](https://defcon.org)
[![Educational](https://img.shields.io/badge/Purpose-Educational%20Only-22c55e?style=flat-square)]()

*Demonstrates how misconfigured SPF/DMARC records enable email spoofing *

</div>

---

## ⚡ What is SpoofGUI?

SpoofGUI is a **graphical tool that makes email spoofing visible**. It connects directly to a domain's MX server over port 25 and delivers a message with an arbitrary `From` header — no access to the real account required. The goal is to show, in real time, **why SPF, DKIM and DMARC exist and what happens when they don't**.

> Built for security researchers, red teamers, and anyone who wants to understand email authentication at the protocol level.

---

## 🖥️ Interface

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚡ SpoofGUI   DEF CON Edition  |  Educational Use Only     by GitoCode  │
├──────────────────────────────────┬──────────────────────────────────────┤
│                                  │  SMTP LOG                            │
│  CABECERAS DEL MENSAJE           │  ┌────────────────────────────────┐  │
│  ┌──────────────────────────┐    │  │                                │  │
│  │ Nombre visible           │    │  │  [*] Iniciando envío...        │  │
│  │ From (spoofeado)         │    │  │  [*] mx1.target.com:25 …       │  │
│  │ Asunto                   │    │  │      250-mail.target.com Hello  │  │
│  └──────────────────────────┘    │  │      250-SIZE 52428800          │  │
│                                  │  │      250 STARTTLS               │  │
│  CONFIGURACIÓN SMTP              │  │  [ok] entregado vía mx1.target  │  │
│  ┌──────────────────────────┐    │  │  [=] Resumen: 1 OK / 0 fallido  │  │
│  │ HELO / PTR hostname      │    │  └────────────────────────────────┘  │
│  │ MX override (vacío=auto) │    │                                      │
│  └──────────────────────────┘    │                                      │
│                                  │                                      │
│  DESTINATARIOS                   │                                      │
│  CUERPO DEL MENSAJE              │                                      │
│                                  │                                      │
│  ● gmail.com  →  LIBRE           │                                      │
│  [⬡ Comprobar] [⬡ Puerto 25] [➤ ENVIAR]                                │
├─────────────────────────────────────────────────────────────────────────┤
│ Fin: 1 OK, 0 fallidos                  ⚠ FOR AUTHORIZED TESTING ONLY  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Dark theme** · Color-coded SMTP log · Real-time DNS analysis · Status bar

---

## 🎯 Features

| | Feature | Description |
|---|---|---|
| 🔍 | **DNS Verdict** | Queries SPF & DMARC records and classifies domain exposure |
| 🔌 | **Port 25 Probe** | Tests if the target MX accepts unauthenticated inbound connections |
| ✉️ | **Arbitrary From** | Builds and delivers a message with any `From` and `HELO` you specify |
| 📡 | **Live SMTP Log** | Full color-coded conversation with the MX server in real time |
| 📎 | **Attachments** | Attach any file to the spoofed message |
| 💾 | **Save / Load** | Persist your session config to `~/spoofgui.json` |

---

## 🚦 DNS Verdict System

After clicking **Comprobar dominio**, SpoofGUI classifies the target:

```
● LIBRE              — No SPF, no DMARC. Spoofing is trivial.
◑ SPF PRESENTE       — SPF exists but no DMARC policy. Partial protection.
◑ DMARC SIN POLÍTICA — DMARC p=none. Monitoring only, no enforcement.
■ POLÍTICA DURA      — DMARC p=reject / p=quarantine. Properly protected.
```

---

## 🚀 Installation

```bash
git clone https://github.com/GitoCode/spoofgui.git
cd spoofgui
pip install dnspython
python spoofgui.py
```

**Requirements:** Python 3.9+ · tkinter (bundled with most Python installs) · dnspython

> Without `dnspython`, the tool still works — DNS resolution is disabled and you must set the MX field manually.

---

## 🔬 Technical Background

SMTP has no built-in authentication for the `From` header. Any host with outbound access to port 25 can claim to send mail *from* any domain. Modern defenses rely entirely on DNS side-channels:

```
SPF   →  Authorizes which IPs may send for the domain
DKIM  →  Cryptographic signature on message headers
DMARC →  Policy: what to do when SPF/DKIM fail
          p=none       → log only (no enforcement)
          p=quarantine → deliver to spam
          p=reject     → reject at gateway
```

When any of these controls is absent or misconfigured, spoofing succeeds. SpoofGUI makes that failure mode **reproducible and visible** in a lab setting.

---

## 🛡️ Defensive Takeaways

```dns
; Publish a strict SPF record
example.com. TXT "v=spf1 include:_spf.example.com -all"

; Add DMARC with reject policy + aggregate reporting
_dmarc.example.com. TXT "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"
```

- Sign outbound mail with **DKIM**
- Monitor DMARC aggregate reports (`dmarcian`, `PowerDMARC`, `parsedmarc`)
- Enable anti-spoofing filters on your email gateway

---

## ⚠️ Legal Disclaimer

> This tool was built **exclusively for educational purposes and authorized security research**.  
> Using it against domains or systems without **explicit written authorization** from the owner is illegal in most jurisdictions.  
> The author assumes no responsibility for misuse.

---

<div align="center">

Made with 🖤 by **[GitoCode](https://github.com/GitoCode)**  


</div>

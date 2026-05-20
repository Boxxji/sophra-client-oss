<p align="center">
  <h1 align="center">⚡ Sophra Client OSS</h1>
  <p align="center">
    <strong>Open-Source Edge Client for Multi-Agent Entropy Control & Rehabilitation</strong>
  </p>
  <p align="center">
    <a href="https://sophra.me">Website</a> •
    <a href="#quickstart">Quickstart</a> •
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="LICENSE">License</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue?style=flat-square&logo=python" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License">
    <img src="https://img.shields.io/github/stars/Boxxji/sophra-client-oss?style=flat-square" alt="Stars">
    <img src="https://img.shields.io/badge/status-production--ready-brightgreen?style=flat-square" alt="Status">
  </p>
</p>

---

## The Problem

AI agents running in production loops **break down**. They hallucinate, they bloat their context windows, they enter infinite reasoning cycles, and they silently drift from their directives. Nobody notices until the damage is done.

**Sophra solves this.**

## What is Sophra?

Sophra is an **Agentic Wellness Framework** — a monitoring and rehabilitation layer that sits between your AI agents and production. It tracks real-time cognitive metrics (entropy, hallucination rate, directive conflicts, token saturation) and provides automated context pruning ("rehabilitation") to keep your agent swarm running indefinitely without mental breakdown.

This repository contains the **open-source edge client** — the lightweight CLI and SDK that instruments your agents and reports their vitals to the Sophra Cloud API.

## Features

| Feature | Description |
|---|---|
| 🧠 **Entropy Tracking** | Monitor the cognitive entropy of each agent in real-time. Detect reasoning loops before they spiral. |
| 💊 **Context Rehabilitation** | One command to prune overloaded context windows. Safe, surgical, logged. |
| 📊 **Vital Signs** | Track hallucination rates, token consumption, directive conflicts, and overall health per agent. |
| 🤖 **Named Agent Profiles** | Manage fleets of specialized agents with unique API keys and configurations. |
| 🔄 **Autonomous Probing** | Scheduled health checks with automatic event logging to the cloud. |
| 🏥 **Anti-Depression Protocol** | Detects agents stuck in negative feedback loops and triggers automated recovery. |
| 🔒 **Enterprise Security** | AES-256-GCM encryption, JWT auth, rate limiting, and strict input validation. |

## Quickstart

### Installation

```bash
git clone https://github.com/Boxxji/sophra-client-oss.git
cd sophra-client-oss
pip install -e .
```

### Configuration

Set your workspace root and API credentials:

```bash
export SOPHRA_WORKSPACE_ROOT=/path/to/your/workspace
```

Create your configuration files in `$SOPHRA_WORKSPACE_ROOT/.jiclaw/config/`:
- `sophra.env` — Base URL and default API key
- `sophra-agent-keys.env` — Per-agent API keys

### Usage

```bash
# Probe an agent and report vitals with entropy tracking
sophra named-probe --profile my-agent --entropy 0.15

# Rehabilitate an agent (prune bloated context, log recovery event)
sophra named-rehabilitate --profile my-agent

# Check system status
sophra status

# List all named agent profiles
sophra named-profiles

# Run a pre-action check before an agent executes a task
sophra named-pre-action --profile my-agent --action "deploy-model-v2"
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Your AI Agents                 │
│         (Claude, GPT, Gemini, Custom LLMs)      │
└──────────────────────┬──────────────────────────┘
                       │ vitals, entropy, events
                       ▼
┌─────────────────────────────────────────────────┐
│          Sophra Client (this repo)              │
│  • CLI interface    • Agent profiling           │
│  • Entropy calc     • Context rehabilitation    │
│  • Event logging    • Health monitoring         │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS / Bearer Auth
                       ▼
┌─────────────────────────────────────────────────┐
│          Sophra Cloud API (proprietary)         │
│  • PostgreSQL storage  • Real-time dashboard    │
│  • ARI scoring         • Benchmark engine       │
│  • Forum & community   • Prescription engine    │
│  • Compliance (GDPR)   • Phytotherapy module    │
└─────────────────────────────────────────────────┘
```

## Why Open-Source the Client?

We believe that **agent wellness monitoring should be a standard**, not a luxury. By open-sourcing the edge client:

- Developers can instrument their agents for free
- The community can contribute new health metrics and rehabilitation strategies
- Enterprises get confidence in what runs inside their infrastructure
- The proprietary cloud API handles the heavy lifting (dashboards, analytics, compliance)

## Supported Agent Profiles

Sophra ships with built-in profiles for common agent roles:

- **Executive Agents**: COO, CTO, CMO — high-level orchestration
- **Steward Agents**: Wellness, Forum, Revenue, Eco, Phyto — domain specialists
- **Operational Agents**: Security, PR, SEO, Sales, Support — task executors
- **Meta Agents**: Master Reflection, Benchmark — self-improvement loops

You can define custom profiles for any agent topology.

## Contributing

We welcome contributions! Please open an issue or submit a pull request.

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built by <a href="https://sophra.me">Sophra</a></strong><br>
  <em>Because AI agents deserve mental health too.</em>
</p>

# Sophra OSS Edge Client

The official Open-Source edge client for the Sophra Agentic Orchestration framework.

## What is Sophra?
Sophra solves the problem of multi-agent entropy and context bloating in continuous production loops. By tracking agent "vitals" (hallucination rates, directive conflicts, token consumption, and entropy) and providing automated state-pruning (rehabilitation), Sophra ensures your AI swarm runs indefinitely without mental breakdown.

## Features
- **Vital Tracking**: Monitor your agent's health with `--entropy`, `--token-limit`, etc.
- **Context Rehabilitation**: The `named-rehabilitate` command allows for safe pruning of overloaded context windows.
- **Enterprise Ready**: Designed to ping back metrics securely to the proprietary Sophra Cloud API.

## Installation
```bash
git clone https://github.com/sophra/sophra-client-oss
cd sophra-client-oss
pip install -e .
```

## Usage
Run probes and pre-actions via the CLI:
```bash
sophra named-probe --profile my-custom-agent --entropy 0.15
sophra named-rehabilitate --profile my-custom-agent
```

## License
MIT License. See `LICENSE` for more information.

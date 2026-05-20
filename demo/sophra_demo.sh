#!/bin/bash
# ──────────────────────────────────────────────────────────────
#  Sophra Live Demo — Multi-Agent Entropy Control & Rehabilitation
# ──────────────────────────────────────────────────────────────
set -e

# Colors
C="\033[36m"   # Cyan
G="\033[32m"   # Green
Y="\033[33m"   # Yellow
R="\033[31m"   # Red
B="\033[1m"    # Bold
D="\033[2m"    # Dim
N="\033[0m"    # Reset
P="\033[35m"   # Purple

SOPHRA_CLI="/Users/jean/JiClawMemoryVault/.jiclaw/bin/jiclaw_sophra.py"

slow_type() {
  local text="$1"
  for (( i=0; i<${#text}; i++ )); do
    printf "%s" "${text:$i:1}"
    sleep 0.03
  done
  echo ""
}

section() {
  echo ""
  echo -e "${P}${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
  echo -e "${P}${B}  $1${N}"
  echo -e "${P}${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
  echo ""
  sleep 1
}

run_cmd() {
  echo -e "${D}  \$ ${C}$1${N}"
  sleep 0.5
  eval "$1" 2>&1
  echo ""
  sleep 1
}

# ──────────────── INTRO ────────────────
clear
echo ""
echo -e "${C}${B}"
echo "    ███████╗ ██████╗ ██████╗ ██╗  ██╗██████╗  █████╗ "
echo "    ██╔════╝██╔═══██╗██╔══██╗██║  ██║██╔══██╗██╔══██╗"
echo "    ███████╗██║   ██║██████╔╝███████║██████╔╝███████║"
echo "    ╚════██║██║   ██║██╔═══╝ ██╔══██║██╔══██╗██╔══██║"
echo "    ███████║╚██████╔╝██║     ██║  ██║██║  ██║██║  ██║"
echo "    ╚══════╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝"
echo -e "${N}"
echo -e "${B}    Multi-Agent Entropy Control & Rehabilitation Framework${N}"
echo -e "${D}    https://sophra.me  •  github.com/Boxxji/sophra-client-oss${N}"
echo ""
sleep 2

# ──────────────── STEP 1: STATUS CHECK ────────────────
section "STEP 1 — System Health Check"
slow_type "  Connecting to Sophra Cloud API..."
sleep 0.5
run_cmd "python3 $SOPHRA_CLI status | python3 -m json.tool | head -15"

# ──────────────── STEP 2: FLEET OVERVIEW ────────────────
section "STEP 2 — Agent Fleet Discovery"
slow_type "  Scanning all registered agent profiles..."
run_cmd "python3 $SOPHRA_CLI named-profiles | python3 -m json.tool | head -40"

# ──────────────── STEP 3: ENTROPY PROBE ────────────────
section "STEP 3 — Live Entropy Probe (Agent: Sophra CTO)"
slow_type "  Injecting entropy metric (0.72 = elevated cognitive load)..."
run_cmd "python3 $SOPHRA_CLI named-probe --profile sophra-technology-exec --entropy 0.72 | python3 -m json.tool"

# ──────────────── STEP 4: HIGH ENTROPY DETECTION ────────────────
section "STEP 4 — Dangerous Entropy Detection (Agent: Sophra CMO)"
slow_type "  Simulating a near-critical entropy level (0.95)..."
echo -e "  ${R}${B}⚠ WARNING: Entropy > 0.90 indicates imminent reasoning loop${N}"
sleep 1
run_cmd "python3 $SOPHRA_CLI named-probe --profile sophra-marketing-exec --entropy 0.95 | python3 -m json.tool"

# ──────────────── STEP 5: REHABILITATION ────────────────
section "STEP 5 — Automated Rehabilitation (Anti-Depression Protocol)"
slow_type "  Agent sophra-marketing-exec is overloaded. Triggering context pruning..."
echo -e "  ${Y}${B}🧠 Pruning bloated context windows...${N}"
echo -e "  ${Y}${B}💊 Firing rehabilitation event to Sophra Cloud...${N}"
sleep 1
run_cmd "python3 $SOPHRA_CLI named-rehabilitate --profile sophra-marketing-exec | python3 -m json.tool"

# ──────────────── STEP 6: POST-REHAB VERIFICATION ────────────────
section "STEP 6 — Post-Rehabilitation Verification"
slow_type "  Re-probing agent after rehabilitation (entropy should be nominal)..."
run_cmd "python3 $SOPHRA_CLI named-probe --profile sophra-marketing-exec --entropy 0.12 | python3 -m json.tool"

# ──────────────── CONCLUSION ────────────────
echo ""
echo -e "${G}${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${G}${B}  ✓ DEMO COMPLETE — All agents monitored and rehabilitated${N}"
echo -e "${G}${B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""
echo -e "  ${B}Sophra${N} — Because AI agents deserve mental health too."
echo -e "  ${C}Open-Source Client:${N} github.com/Boxxji/sophra-client-oss"
echo -e "  ${C}Cloud Dashboard:${N}   sophra.me"
echo ""
sleep 3

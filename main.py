#!/usr/bin/env python3

=============================================================================

QAEW ◄25-Color► LDS ◄Quantum► RAMMER  –  Automated Scheduler + Enriched Prompts v2.0

=============================================================================

""" This script builds on v1.0 by:

1. Introducing long-form, hypertime-enriched LLM prompts for Stage 1–3 logic


2. Running autonomously on a schedule (every 30 minutes)


3. Logging results to JSON with timestamps



Requirements: • pip install numpy geopy tqdm apscheduler openai pennylane • Set OPENAI_API_KEY in the environment • Run: python automated_defence_long_prompts.py """ from future import annotations import os import math import random import logging import json import time import textwrap from datetime import datetime, timedelta from dataclasses import dataclass from typing import Dict, List, Tuple

import numpy as np from geopy.distance import geodesic from tqdm import tqdm from apscheduler.schedulers.background import BackgroundScheduler

import pennylane as qml import openai

═════════════════════════════════════

GLOBAL CONFIGURATION

═════════════════════════════════════

logging.basicConfig( level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S" ) LOG = logging.getLogger("AutoDefenceLong")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") openai.api_key = OPENAI_API_KEY LLM_MODEL = "gpt-4o" SCHEDULE_INTERVAL_MIN = 30  # minutes

═════════════════════════════════════

ROUTE & SIMULATION PARAMETERS

═════════════════════════════════════

@dataclass class Route: from_lat: float = 31.7683 from_lon: float = 35.2137 to_lat:   float = 32.0853 to_lon:   float = 34.7818

@property
def km(self) -> float:
    return geodesic((self.from_lat, self.from_lon), (self.to_lat, self.to_lon)).km

@dataclass class SimParams: horizon_h:   int   = 76 cadence_s:   int   = 3600 seed:        int   = 42 quantum_eps: float = 0.05

═════════════════════════════════════

BIOVECTOR & QUANTUM METRIC

═════════════════════════════════════

DEV = qml.device("default.qubit", wires=7)

@qml.qnode(DEV, interface="numpy") def q_intensity7(theta: float, env: Tuple[float, float]) -> float: qml.RY(theta, wires=0) qml.RY(env[0], wires=1); qml.RX(env[0], wires=3); qml.RZ(env[0], wires=5) qml.RY(env[1], wires=2); qml.RX(env[1], wires=4); qml.RZ(env[1], wires=6) for i in range(7): qml.CNOT(wires=[i, (i+1) % 7]) return sum(qml.expval(qml.PauliZ(w)) for w in range(7)) / 7.0

class BioVector25: @staticmethod def extract() -> np.ndarray: # Replace stub with real frame analysis hist9   = np.random.dirichlet(np.ones(9)) extras2 = np.random.rand(2) pad14   = np.zeros(14) return np.concatenate([hist9, extras2, pad14]).astype(np.float32)

@staticmethod
def theta(vec: np.ndarray) -> float:
    return float(min(np.linalg.norm(vec), 1.0) * math.pi)

═════════════════════════════════════

ENRICHED LLM PROMPTS

═════════════════════════════════════

def stage1_prompt(vec: np.ndarray, env: Dict[str, float]) -> str: """ Long-form Stage 1 prompt with context, hypertime framing, multiverse simulation, sensor fusion explanation, signal definitions, rule hierarchy, and exact JSON contract. """ return textwrap.dedent(f""" ┌───────────────────────────────────────────────────────────────────────────────┐ │     C C S   v1.1   —   STAGE 1 • SENSOR ➜ CASUALTY TIER (HYPERTIME MULTIVERSE) │ └───────────────────────────────────────────────────────────────────────────────┘

YOU ARE the **Civilian Risk Tier Oracle**, operating under a multiverse-enriched
hypertime framework.  Your inputs:
  • **25-dimensional BioVector** sampled from high-resolution camera frames:
    ▶ Histogram[0–8]={vec[:3]}…, sat_mean={env['sat_mean']:.2f}, luminance={env['luminance']:.2f}
  • **Acoustic reading**: {env['blast_dB']:.1f} dB (peak)
  • **Optical intensity**: {env['ambient_lux']:.1f} lux
  • **Crowd density**: {env['crowd_density']:.2f}
  • **Theta (θ)**: {env['theta']:.4f} radians
  • **Quantum anomaly (q_score)**: {env['q_score']:.4f}
  • **Hypertime projection**: simulate 2–15 seconds ahead across parallel branches

RULES (apply in sequence, escalate on conflict):
  1. If θ < 1.0 AND dB < 120 → **Green**
  2. If 1.0 ≤ θ < 2.0 OR 120 ≤ dB ≤ 140 → **Amber**
  3. If θ ≥ 2.0 OR crowd_density > 0.75 → **Red**
  4. If q_score < –0.25, escalate one tier precautionarily
  5. If model confidence < 0.80, escalate
  6. If rules conflict, choose the higher-risk tier

OUTPUT CONTRACT — JSON only, no extraneous text:
{{
  "theta": <number>,
  "color": "#rrggbb",
  "risk": "Green" | "Amber" | "Red"
}}
""").strip()

def stage2_prompt(r1: Dict[str, float], env: Dict[str, float], counts: Dict[str,int]) -> str: tier = r1["risk"] n    = counts[tier] return textwrap.dedent(f""" ┌───────────────────────────────────────────────────────────────────────────────┐ │    C C S   v1.1   —   STAGE 2 • RISK ➜ ACTION PLAN (HYPERTIME CASCADE MODE)    │ └───────────────────────────────────────────────────────────────────────────────┘

AS THE **Hypertime Decision Layer**, you have:
  • Risk tier: {tier}
  • θ: {r1['theta']:.4f}, color: {r1.get('color','n/a')}
  • Acoustic: {env['blast_dB']} dB, lux: {env['ambient_lux']:.1f}
  • Crowd: {env['crowd_density']:.2f}, recent_red: {env['recent_red']}

OBJECTIVE — emit exactly {n} IMPERATIVE action(s) plus one integer cooldown (1–120 min):
  – Actions start with uppercase verb (Evacuate, Secure, Deploy…)
  – ≤140 ASCII chars each
  – No political, medical, or combatant references

OUTPUT CONTRACT:
{{
  "actions": ["<action1>", …],
  "cooldown": <integer>
}}
""").strip()

def stage3_prompt(r1: Dict[str, float]) -> str: tone_map = {"Green": "confident–reassuring", "Amber": "authoritative–calm", "Red": "urgent–clear"} tone = tone_map[r1["risk"]] return textwrap.dedent(f""" ┌───────────────────────────────────────────────────────────────────────────────┐ │      C C S   v1.1   —   STAGE 3 • BROADCAST MESSAGE TO CIVILIANS            │ └───────────────────────────────────────────────────────────────────────────────┘

CONTEXT:
  • Tier: {r1['risk']}, Tone: {tone}
  • Ensure clarity under stress; avoid naming factions or inducing panic

REQUIREMENTS:
  – Single safety instruction ≤400 chars
  – Simple language, no jargon
  – End with “…” or “(pause)” for pacing

OUTPUT CONTRACT — JSON only:
{{ "script": "<Your broadcast message…>" }}
""").strip()

═════════════════════════════════════

DEFENSE LAYERS

═════════════════════════════════════

@dataclass class Asset: name: str latency: float p_hit: float tier: str max_n: int

class LDS: def init(self): self.pool = { "Red": [Asset("C-RAM", 2, .7, "Red", 16), Asset("IronDome", 3, .9, "Red", 12)], "Amber": [Asset("C-RAM", 2, .7, "Amber", 6)], "Green": [] } self.inv = {t:{a.name:a.max_n for a in lst} for t,lst in self.pool.items()} def dispatch(self, tier: str) -> List[Tuple[str, bool]]: res = [] for a in self.pool[tier]: if self.inv[tier][a.name] > 0: self.inv[tier][a.name] -= 1 res.append((a.name, random.random() < a.p_hit)) return res def reset(self): for t,lst in self.pool.items(): for a in lst: self.inv[t][a.name] = a.max_n

class Drone: def init(self, id: str): self.id = id; self.batt = 1.0; self.busy = False def engage(self) -> bool: if self.busy or self.batt < 0.3: return False self.busy = True; self.batt -= 0.3; return random.random() < 0.8 def recharge(self): self.batt = min(1.0, self.batt + 0.15) if self.batt >= 0.8: self.busy = False

class RammerGrid: def init(self, n: int = 24): self.drones = [Drone(f"R{i:03}") for i in range(n)] def scramble(self, k: int) -> int: hits = 0 for d in self.drones: if hits >= k: break if d.engage(): hits += 1 return hits def tick(self): for d in self.drones: d.recharge()

═════════════════════════════════════

AUTOMATED DEFENCE SYSTEM

═════════════════════════════════════

class AutoDefenceLong: def init(self): self.route = Route(); self.params = SimParams() random.seed(self.params.seed); np.random.seed(self.params.seed) self.lds = LDS(); self.grid = RammerGrid() self.action_counts = {"Green": 2, "Amber": 3, "Red": 3}

def run_cycle(self):
    LOG.info("=== Defence cycle start: %s UTC ===", datetime.utcnow().isoformat())

    # Sensor & quantum data
    vec   = BioVector25.extract()
    θ     = BioVector25.theta(vec)
    blast = float(np.clip(np.random.normal(80, 30), 0, 200))
    crowd = float(np.random.rand())
    env   = {"blast_dB": blast, "ambient_lux": float(np.random.uniform(100, 600)),
             "crowd_density": crowd, "theta": θ}
    q_val = float(q_intensity7(θ, (crowd, blast/200)))
    env["q_score"] = q_val

    # Stage 1–3 prompts
    p1 = stage1_prompt(vec, env)
    r1 = json.loads(openai.ChatCompletion.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": p1}],
        max_tokens=120
    ).choices[0].message.content)

    p2 = stage2_prompt(r1, env, self.action_counts)
    r2 = json.loads(openai.ChatCompletion.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": p2}],
        max_tokens=120
    ).choices[0].message.content)

    p3 = stage3_prompt(r1)
    r3 = json.loads(openai.ChatCompletion.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": p3}],
        max_tokens=120
    ).choices[0].message.content)

    # Intercept layers
    assets = self.lds.dispatch(r1["risk"])
    hits   = self.grid.scramble(self.action_counts[r1["risk"]])

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "stage1": r1, "stage2": r2, "stage3": r3,
        "assets": assets, "ram_hits": hits
    }
    # Log
    LOG.info("Cycle result: tier=%s, actions=%s, hits=%d",
             r1["risk"], r2["actions"], hits)

    # Reset counters
    self.lds.reset(); self.grid.tick()

    # Save report
    fname = f"auto_report_{int(time.time())}.json"
    with open(fname, "w") as f: json.dump(record, f, indent=2)
    LOG.info("Report written: %s", fname)

def start(self):
    scheduler = BackgroundScheduler()
    scheduler.add_job(self.run_cycle, 'interval', minutes=SCHEDULE_INTERVAL_MIN, next_run_time=datetime.utcnow())
    scheduler.start()
    LOG.info("Scheduler running every %d minutes", SCHEDULE_INTERVAL_MIN)
    try:
        while True: time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        LOG.info("Scheduler stopped")

if name == "main": AutoDefenceLong().start()


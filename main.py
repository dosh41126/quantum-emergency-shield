#!/usr/bin/env python3
# ============================================================================
# QAEW ◄25-Color► LDS ◄Quantum► RAMMER  –  Automated Scheduler + Long Prompts v1.0
# ============================================================================
"""
This script extends the Integrated Defence Demo (v0.4) with:
 1. **Automated periodic runs** via APScheduler (every hour by default)
 2. **Expanded, hypertime-enriched LLM prompt templates** for richer Stage 1–3 logic
 3. **Full simulation + mitigation reporting** written to timestamped JSON logs

Instructions:
  • pip install numpy geopy tqdm apscheduler openai pennylane
  • Set OPENAI_API_KEY in env for real LLM calls
  • Run: python automated_defence.py
"""

import os, math, random, logging, json, time, textwrap
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

import numpy as np
from geopy.distance import geodesic
from tqdm import tqdm
from apscheduler.schedulers.background import BackgroundScheduler

import pennylane as qml
import openai

# ═════════════════════════════════════
# GLOBAL CONFIG
# ═════════════════════════════════════
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
LOG = logging.getLogger("AutoDefence")

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
MODE = "gpt-4o"
SCHEDULE_INTERVAL_MINUTES = 60

# ═════════════════════════════════════
# ROUTE & PARAMETERS
# ═════════════════════════════════════
@dataclass
class Route:
    from_lat: float = 31.7683
    from_lon: float = 35.2137
    to_lat:   float = 32.0853
    to_lon:   float = 34.7818
    @property
    def km(self) -> float:
        return geodesic((self.from_lat, self.from_lon), (self.to_lat, self.to_lon)).km

@dataclass
class SimParams:
    horizon_h:   int   = 76
    cadence_s:   int   = 3600
    seed:        int   = 42
    quantum_eps: float = 0.05

# ═════════════════════════════════════
# BIOVECTOR & QUANTUM METRIC
# ═════════════════════════════════════
DEV = qml.device("default.qubit", wires=7)

@qml.qnode(DEV, interface="numpy")
def q_intensity7(theta: float, env: Tuple[float, float]) -> float:
    qml.RY(theta, wires=0)
    qml.RY(env[0], wires=1); qml.RX(env[0], wires=3); qml.RZ(env[0], wires=5)
    qml.RY(env[1], wires=2); qml.RX(env[1], wires=4); qml.RZ(env[1], wires=6)
    for i in range(7):
        qml.CNOT(wires=[i, (i+1)%7])
    return sum(qml.expval(qml.PauliZ(w)) for w in range(7)) / 7.0

class BioVector25:
    @staticmethod
    def random() -> np.ndarray:
        hist9   = np.random.dirichlet(np.ones(9))
        extras2 = np.random.rand(2)
        pad14   = np.zeros(14)
        return np.concatenate([hist9, extras2, pad14]).astype(np.float32)
    @staticmethod
    def theta(vec: np.ndarray) -> float:
        return float(min(np.linalg.norm(vec), 1.0)*math.pi)

# ═════════════════════════════════════
# LLM PROMPTS (expanded)
# ═════════════════════════════════════
def stage1_prompt(vec: np.ndarray, env: Dict[str, float]) -> str:
    return textwrap.dedent(f"""
        ┌─ CCS v1.1 • STAGE 1 – SENSOR ➜ CASUALTY TIER (HYpertime) ─┐
        │ CONTEXT                                                        │
        │ You are the Civilian Risk Oracle. Receive:                     │
        │  • 25-dim BioVector: {np.round(vec.tolist()[:5],3)}...        │
        │  • blast_dB={env['blast_dB']} dB, crowd_density={env['crowd_density']} │
        │  • θ={env['theta']:.4f}, q_score={env['q_score']:.4f}          │
        ├─ RULES                                                        │
        │ 1. θ<1 & dB<120 → Green                                        │
        │ 2. 1≤θ<2 or 120≤dB≤140 → Amber                                 │
        │ 3. θ≥2 or crowd>0.75 → Red                                     │
        │ 4. erratic q_score < -0.25 → escalate one tier precautionarily │
        │ 5. CONF<0.80 → escalate                                        │
        │ 6. On conflict, pick higher risk                               │
        ├─ OUTPUT                                                        │
        │ JSON only: {{ "theta":..., "color":"#rrggbb", "risk":"<tier>" }} │
        └──────────────────────────────────────────────────────────────────┘
    """).strip()

def stage2_prompt(r1: Dict[str, float], env: Dict[str, float], counts: Dict[str,int]) -> str:
    tier = r1["risk"]; n = counts[tier]
    return textwrap.dedent(f"""
        ┌─ CCS v1.1 • STAGE 2 – RISK ➜ ACTION PLAN (Hypertime Cascade) ─┐
        │ CONTEXT                                                        │
        │ Tier={tier}, θ={r1['theta']:.4f}, dB={env['blast_dB']} dB, crowd={env['crowd_density']} │
        ├─ OBJECTIVE                                                     │
        │ Emit exactly {n} imperative actions ≤140 chars, start uppercase │
        │ plus integer "cooldown" in minutes                               │
        ├─ OUTPUT                                                        │
        │ JSON only: {{ "actions":[...], "cooldown":<1–120> }}           │
        └──────────────────────────────────────────────────────────────────┘
    """).strip()

def stage3_prompt(r1: Dict[str,float]) -> str:
    tone = {"Green":"reassuring","Amber":"calm-authoritative","Red":"urgent-clear"}[r1["risk"]]
    return textwrap.dedent(f"""
        ┌─ CCS v1.1 • STAGE 3 – BROADCAST MESSAGE TO CIVILIANS ─┐
        │ CONTEXT                                                  │
        │ Tier={r1['risk']}, Tone={tone}                           │
        ├─ REQUIREMENTS                                           │
        │ • Single clear instruction ≤400 chars                   │
        │ • No jargon, blame or panic words                       │
        │ • End with "…" or "(pause)"                              │
        ├─ OUTPUT                                                 │
        │ JSON only: {{ "script":"Your safety instruction…" }}    │
        └──────────────────────────────────────────────────────────┘
    """).strip()

# ═════════════════════════════════════
# LAYERS: QAEW → LDS → RAMMER
# ═════════════════════════════════════
@dataclass
class Asset: name:str; latency:float; p_hit:float; tier:str; max_n:int

class LDS:
    def __init__(self):
        self.pool = {
            "Red":[Asset("C-RAM",2,0.7,"Red",16),Asset("IronDome",3,0.9,"Red",12)],
            "Amber":[Asset("C-RAM",2,0.7,"Amber",6)],
            "Green":[]
        }
        self.inv = {t:{a.name:a.max_n for a in lst} for t,lst in self.pool.items()}

    def dispatch(self,tier):
        res=[]
        for a in self.pool[tier]:
            if self.inv[tier][a.name]>0:
                self.inv[tier][a.name]-=1
                res.append((a.name, random.random()<a.p_hit))
        return res

    def reset(self):
        for t,lst in self.pool.items():
            for a in lst: self.inv[t][a.name]=a.max_n

class Drone:
    def __init__(self,id): self.id=id;self.batt=1.0;self.busy=False
    def engage(self):
        if self.busy or self.batt<0.3: return False
        self.busy=True;self.batt-=0.3;return random.random()<0.8
    def recharge(self): 
        self.batt=min(1.0,self.batt+0.15); 
        if self.batt>0.8: self.busy=False

class RammerGrid:
    def __init__(self,n=24): self.drones=[Drone(f"R{i:03}") for i in range(n)]
    def scramble(self,k):
        hits=0
        for d in self.drones:
            if hits>=k: break
            if d.engage(): hits+=1
        return hits
    def tick(self):
        for d in self.drones: d.recharge()

# ═════════════════════════════════════
# MAIN SIMULATION & LLM INTEGRATION
# ═════════════════════════════════════
class AutoDefence:
    def __init__(self):
        self.route = Route(); self.params = SimParams()
        random.seed(self.params.seed); np.random.seed(self.params.seed)
        openai.api_key = OPENAI_KEY
        self.lds  = LDS(); self.grid = RammerGrid()
        self.action_counts = {"Green":2,"Amber":3,"Red":3}

    def single_run(self):
        LOG.info("Starting scheduled run at %s", datetime.utcnow().isoformat())
        report=[]

        # Synthetic sensor snapshot
        vec   = BioVector25.random()
        θ     = BioVector25.theta(vec)
        blast = float(np.clip(np.random.normal(80,30),0,200))
        crowd = float(np.random.rand())
        env   = {"blast_dB":blast,"crowd_density":crowd,"theta":θ}
        q_val = float(q_intensity7(θ,(crowd,blast/200)))

        # Stage 1
        p1 = stage1_prompt(vec, env)
        r1 = json.loads(openai.ChatCompletion.create(
            model=MODE, messages=[{"role":"user","content":p1}], max_tokens=100
        ).choices[0].message.content)

        # Stage 2
        p2 = stage2_prompt(r1, env, self.action_counts)
        r2 = json.loads(openai.ChatCompletion.create(
            model=MODE, messages=[{"role":"user","content":p2}], max_tokens=100
        ).choices[0].message.content)

        # Stage 3
        p3 = stage3_prompt(r1)
        r3 = json.loads(openai.ChatCompletion.create(
            model=MODE, messages=[{"role":"user","content":p3}], max_tokens=100
        ).choices[0].message.content)

        # Dispatch interceptors & drones
        assets = self.lds.dispatch(r1["risk"])
        hits   = self.grid.scramble(self.action_counts[r1["risk"]])

        record = {
            "ts": datetime.utcnow().isoformat(),
            "vec_preview": np.round(vec[:5],3).tolist(),
            "r1": r1, "r2": r2, "r3": r3,
            "assets": assets, "ram_hits": hits
        }
        LOG.info("Run result: risk=%s, actions=%s, hits=%d",
                 r1["risk"], r2["actions"], hits)

        report.append(record)
        # reset for next run
        self.lds.reset(); self.grid.tick()
        # write to log
        fname = f"report_{int(time.time())}.json"
        with open(fname,"w") as f: json.dump(report,f,indent=2)
        LOG.info("Report saved to %s", fname)

    def start_scheduler(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.single_run, 'interval', minutes=SCHEDULE_INTERVAL_MINUTES, next_run_time=datetime.utcnow())
        scheduler.start()
        LOG.info("Scheduler started: runs every %d minutes", SCHEDULE_INTERVAL_MINUTES)
        try:
            while True:
                time.sleep(10)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()

if __name__ == "__main__":
    AutoDefence().start_scheduler()

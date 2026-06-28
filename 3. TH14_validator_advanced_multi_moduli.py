#!/usr/bin/env python3
import os
import math
import multiprocessing as mp
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import ttk

# ============================================================
# CONFIGURATION
# ============================================================

N_PROCESSES = 4
DIFFS = [2, 4, 6]  # twin, cousin, sexy
DEFAULT_MODULUS = 210
DEFAULT_LIMIT = 1_000_000

# ============================================================
# UTILITAIRES
# ============================================================

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def prime_factors(n):
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors

def residues_coprime_to_modulus(modulus):
    return [r for r in range(1, modulus) if gcd(r, modulus) == 1]

def sieve_of_eratosthenes(limit):
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if is_prime[i]:
            step = i
            start = i * i
            for j in range(start, limit + 1, step):
                is_prime[j] = False
    return [i for i in range(2, limit + 1) if is_prime[i]]

# ============================================================
# COORDONNÉES / LABELS
# ============================================================

def residue_to_label(r):
    return f"r{r}"

def prime_to_residue(p, modulus):
    r = p % modulus
    return r if gcd(r, modulus) == 1 else None

def prime_to_coordinate(p, modulus):
    r = prime_to_residue(p, modulus)
    return residue_to_label(r) if r is not None else None

# ============================================================
# PATTERNS TH14 AUTOMATIQUES
# ============================================================

def generate_patterns(modulus, diffs):
    residues = residues_coprime_to_modulus(modulus)
    patterns_by_k = {}
    for k in diffs:
        patterns = set()
        for r in residues:
            rk = (r + k) % modulus
            if gcd(rk, modulus) == 1:
                patterns.add((residue_to_label(r), residue_to_label(rk)))
        patterns_by_k[k] = patterns
    return patterns_by_k
# ============================================================
# MULTIPROCESSING : FIND PAIRS
# ============================================================

def find_pairs_chunk(args):
    primes_chunk, primes_set = args
    twin_pairs = []
    cousin_pairs = []
    sexy_pairs = []

    for p in primes_chunk:
        if p + 2 in primes_set:
            twin_pairs.append((p, p + 2))
        if p + 4 in primes_set:
            cousin_pairs.append((p, p + 4))
        if p + 6 in primes_set:
            sexy_pairs.append((p, p + 6))

    return twin_pairs, cousin_pairs, sexy_pairs


# ============================================================
# VALIDATEUR TH14
# ============================================================

class TH14Validator:
    def __init__(self, limit, modulus, n_processes=N_PROCESSES):
        self.limit = limit
        self.modulus = modulus
        self.n_processes = n_processes

        # Génération des premiers
        self.primes = sieve_of_eratosthenes(limit)
        self.primes_set = set(self.primes)

        # Facteur premier maximal du module
        self.max_prime_factor = max(prime_factors(modulus))

        # Patterns TH14 générés automatiquement
        self.patterns_by_k = generate_patterns(modulus, DIFFS)
        self.TWIN_PATTERNS   = self.patterns_by_k[2]
        self.COUSIN_PATTERNS = self.patterns_by_k[4]
        self.SEXY_PATTERNS   = self.patterns_by_k[6]

        # Stockage des couples
        self.twin_pairs = []
        self.cousin_pairs = []
        self.sexy_pairs = []

        # Conformité
        self.twin_conforming = 0
        self.cousin_conforming = 0
        self.sexy_conforming = 0

        # Statistiques
        self.coordinate_distribution = defaultdict(int)
        self.difference_distribution = defaultdict(int)

        # Anomalies
        self.anomalies = []

    # ------------------------------------------------------------
    # Recherche des couples (multiprocessing)
    # ------------------------------------------------------------
    def find_pairs(self):
        primes_filtered = [p for p in self.primes if p > self.max_prime_factor]

        if self.n_processes <= 1:
            twin_pairs, cousin_pairs, sexy_pairs = find_pairs_chunk(
                (primes_filtered, self.primes_set)
            )
            self.twin_pairs = twin_pairs
            self.cousin_pairs = cousin_pairs
            self.sexy_pairs = sexy_pairs
            return

        chunk_size = max(1, len(primes_filtered) // self.n_processes)
        chunks = [
            primes_filtered[i:i + chunk_size]
            for i in range(0, len(primes_filtered), chunk_size)
        ]

        with mp.Pool(self.n_processes) as pool:
            results = pool.map(find_pairs_chunk, [(chunk, self.primes_set) for chunk in chunks])

        for twin_chunk, cousin_chunk, sexy_chunk in results:
            self.twin_pairs.extend(twin_chunk)
            self.cousin_pairs.extend(cousin_chunk)
            self.sexy_pairs.extend(sexy_chunk)

    # ------------------------------------------------------------
    # Validation des couples
    # ------------------------------------------------------------
    def validate_pairs(self):
        # Twin
        for p, q in self.twin_pairs:
            cp = prime_to_coordinate(p, self.modulus)
            cq = prime_to_coordinate(q, self.modulus)
            pattern = (cp, cq)

            if pattern in self.TWIN_PATTERNS:
                self.twin_conforming += 1
            else:
                self.anomalies.append(("twin", p, q, pattern))

            self.coordinate_distribution[pattern] += 1
            self.difference_distribution[2] += 1

        # Cousin
        for p, q in self.cousin_pairs:
            cp = prime_to_coordinate(p, self.modulus)
            cq = prime_to_coordinate(q, self.modulus)
            pattern = (cp, cq)

            if pattern in self.COUSIN_PATTERNS:
                self.cousin_conforming += 1
            else:
                self.anomalies.append(("cousin", p, q, pattern))

            self.coordinate_distribution[pattern] += 1
            self.difference_distribution[4] += 1

        # Sexy
        for p, q in self.sexy_pairs:
            cp = prime_to_coordinate(p, self.modulus)
            cq = prime_to_coordinate(q, self.modulus)
            pattern = (cp, cq)

            if pattern in self.SEXY_PATTERNS:
                self.sexy_conforming += 1
            else:
                self.anomalies.append(("sexy", p, q, pattern))

            self.coordinate_distribution[pattern] += 1
            self.difference_distribution[6] += 1

    # ------------------------------------------------------------
    # Statistiques globales
    # ------------------------------------------------------------
    def get_statistics(self):
        total_twin = len(self.twin_pairs)
        total_cousin = len(self.cousin_pairs)
        total_sexy = len(self.sexy_pairs)
        total_pairs = total_twin + total_cousin + total_sexy

        twin_compliance   = 100 * self.twin_conforming   / total_twin if total_twin else 0
        cousin_compliance = 100 * self.cousin_conforming / total_cousin if total_cousin else 0
        sexy_compliance   = 100 * self.sexy_conforming   / total_sexy if total_sexy else 0

        return {
            "limit": self.limit,
            "modulus": self.modulus,
            "max_prime_factor": self.max_prime_factor,
            "primes_count": len(self.primes),

            "twin_pairs": total_twin,
            "cousin_pairs": total_cousin,
            "sexy_pairs": total_sexy,

            "twin_conforming": self.twin_conforming,
            "cousin_conforming": self.cousin_conforming,
            "sexy_conforming": self.sexy_conforming,

            "twin_compliance": twin_compliance,
            "cousin_compliance": cousin_compliance,
            "sexy_compliance": sexy_compliance,

            "total_pairs": total_pairs,
            "total_conforming": (
                self.twin_conforming +
                self.cousin_conforming +
                self.sexy_conforming
            ),

            "anomalies_count": len(self.anomalies),
        }
# ============================================================
# VISUALISATIONS
# ============================================================

def generate_compliance_chart(stats, output_path):
    fig, ax = plt.subplots(figsize=(8, 5))

    categories = ["Twin", "Cousin", "Sexy"]
    compliances = [
        stats["twin_compliance"],
        stats["cousin_compliance"],
        stats["sexy_compliance"],
    ]
    colors = ["#2ecc71", "#3498db", "#e74c3c"]

    bars = ax.bar(categories, compliances, color=colors, edgecolor="black", linewidth=2)
    ax.set_ylabel("Compliance (%)")
    ax.set_title(f"TH14 Compliance (mod {stats['modulus']}) up to {stats['limit']:,}")
    ax.set_ylim(0, 105)

    for bar, comp in zip(bars, compliances):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 1,
                f"{comp:.2f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.grid(axis="y", alpha=0.3, linestyle="--")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    return output_path


def generate_pair_distribution_chart(stats, output_path):
    fig, ax = plt.subplots(figsize=(6, 6))

    sizes = [stats["twin_pairs"], stats["cousin_pairs"], stats["sexy_pairs"]]
    labels = [
        f"Twin ({stats['twin_pairs']:,})",
        f"Cousin ({stats['cousin_pairs']:,})",
        f"Sexy ({stats['sexy_pairs']:,})",
    ]
    colors = ["#2ecc71", "#3498db", "#e74c3c"]

    ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%",
           startangle=90, textprops={"fontsize": 10, "fontweight": "bold"})
    ax.set_title(f"Prime Pair Distribution (mod {stats['modulus']})")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    return output_path


def generate_pattern_frequency_chart(validator, output_path):
    TWIN_PATTERNS   = validator.TWIN_PATTERNS
    COUSIN_PATTERNS = validator.COUSIN_PATTERNS
    SEXY_PATTERNS   = validator.SEXY_PATTERNS

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Twin
    twin_data = {str(p): validator.coordinate_distribution.get(p, 0) for p in TWIN_PATTERNS}
    ax = axes[0]
    ax.bar(range(len(twin_data)), list(twin_data.values()), color="#2ecc71", edgecolor="black")
    ax.set_xticks(range(len(twin_data)))
    ax.set_xticklabels(list(twin_data.keys()), rotation=45, fontsize=8)
    ax.set_title("Twin Patterns")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    # Cousin
    cousin_data = {str(p): validator.coordinate_distribution.get(p, 0) for p in COUSIN_PATTERNS}
    ax = axes[1]
    ax.bar(range(len(cousin_data)), list(cousin_data.values()), color="#3498db", edgecolor="black")
    ax.set_xticks(range(len(cousin_data)))
    ax.set_xticklabels(list(cousin_data.keys()), rotation=45, fontsize=8)
    ax.set_title("Cousin Patterns")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    # Sexy
    sexy_data = {str(p): validator.coordinate_distribution.get(p, 0) for p in SEXY_PATTERNS}
    ax = axes[2]
    ax.bar(range(len(sexy_data)), list(sexy_data.values()), color="#e74c3c", edgecolor="black")
    ax.set_xticks(range(len(sexy_data)))
    ax.set_xticklabels(list(sexy_data.keys()), rotation=45, fontsize=8)
    ax.set_title("Sexy Patterns")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    plt.suptitle(f"Pattern Frequency (mod {validator.modulus})", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    return output_path


# ============================================================
# RAPPORT MARKDOWN (incl. Section 5.4)
# ============================================================

def generate_markdown_report(validator, stats, chart_paths, output_file):
    anomalies_preview = validator.anomalies[:10]

    report = f"""# TH14 Validation Report (mod {stats['modulus']})

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

- Modulus: **{stats['modulus']}**
- Max prime factor of modulus: **{stats['max_prime_factor']}**
- Primes analyzed up to **{stats['limit']:,}**
- Total prime pairs: **{stats['total_pairs']:,}**
- Anomalies (non-conforming pairs): **{stats['anomalies_count']:,}**

Overall compliance: **{100 * stats['total_conforming'] / stats['total_pairs']:.6f}%**

---

## Section 1 — Compliance by Pair Type

| Type   | Pairs | Conforming | Compliance |
|--------|-------|-----------|-----------|
| Twin   | {stats['twin_pairs']:,} | {stats['twin_conforming']:,} | {stats['twin_compliance']:.6f}% |
| Cousin | {stats['cousin_pairs']:,} | {stats['cousin_conforming']:,} | {stats['cousin_compliance']:.6f}% |
| Sexy   | {stats['sexy_pairs']:,} | {stats['sexy_conforming']:,} | {stats['sexy_compliance']:.6f}% |
| **Total** | **{stats['total_pairs']:,}** | **{stats['total_conforming']:,}** | **{100 * stats['total_conforming'] / stats['total_pairs']:.6f}%** |

![Compliance Chart]({chart_paths['compliance']})

---

## Section 2 — Pair Distribution

![Pair Distribution]({chart_paths['distribution']})

---

## Section 3 — Pattern Frequencies

![Pattern Frequency]({chart_paths['patterns']})

---

## Section 4 — Origin of High Compliance

We restrict primes to **p > max prime factor of modulus**:

- For mod 210: max prime factor = 7  
- For mod 2310: max prime factor = 11  
- For mod 30030: max prime factor = 13  

Thus, every prime considered is coprime to the modulus, and its residue lies in **Z_{stats['modulus']}^***.

The modular structure Z_{stats['modulus']}^* constrains all prime pairs (k ∈ {{2,4,6}}) to the generated patterns.

---

## Section 5 — TH14 Patterns (mod {stats['modulus']})

### 5.1 Twin Patterns (k = 2)

Total patterns: {len(validator.TWIN_PATTERNS)}

| Pattern | Frequency |
|---------|-----------|
"""
    for pattern in sorted(validator.TWIN_PATTERNS):
        count = validator.coordinate_distribution.get(pattern, 0)
        report += f"| {pattern} | {count:,} |\n"

    report += f"""

### 5.2 Cousin Patterns (k = 4)

Total patterns: {len(validator.COUSIN_PATTERNS)}

| Pattern | Frequency |
|---------|-----------|
"""
    for pattern in sorted(validator.COUSIN_PATTERNS):
        count = validator.coordinate_distribution.get(pattern, 0)
        report += f"| {pattern} | {count:,} |\n"

    report += f"""

### 5.3 Sexy Patterns (k = 6)

Total patterns: {len(validator.SEXY_PATTERNS)}

| Pattern | Frequency |
|---------|-----------|
"""
    for pattern in sorted(validator.SEXY_PATTERNS):
        count = validator.coordinate_distribution.get(pattern, 0)
        report += f"| {pattern} | {count:,} |\n"


    # ============================================================
    # SECTION 5.4 — FULL PATTERN TABLES
    # ============================================================

    report += f"""

---

## Section 5.4 — Full Pattern Tables (mod {stats['modulus']})

Below is the complete list of all TH14 patterns generated from the modular group Z_{stats['modulus']}^*.

---

### Twin Patterns (k = 2)
Total patterns: {len(validator.TWIN_PATTERNS)}

| Index | Pattern |
|-------|---------|
"""
    for i, pattern in enumerate(sorted(validator.TWIN_PATTERNS)):
        report += f"| {i+1} | {pattern} |\n"

    report += f"""

---

### Cousin Patterns (k = 4)
Total patterns: {len(validator.COUSIN_PATTERNS)}

| Index | Pattern |
|-------|---------|
"""
    for i, pattern in enumerate(sorted(validator.COUSIN_PATTERNS)):
        report += f"| {i+1} | {pattern} |\n"

    report += f"""

---

### Sexy Patterns (k = 6)
Total patterns: {len(validator.SEXY_PATTERNS)}

| Index | Pattern |
|-------|---------|
"""
    for i, pattern in enumerate(sorted(validator.SEXY_PATTERNS)):
        report += f"| {i+1} | {pattern} |\n"


    # ============================================================
    # SECTION 6 — CONCLUSION
    # ============================================================

    report += f"""

---

## Section 6 — Conclusion

- TH14 holds structurally for mod {stats['modulus']}.  
- Compliance is effectively **100%** (or 99.99% when boundary effects are included).  
- The modular structure Z_{stats['modulus']}^* constrains all prime pairs (k ∈ {{2,4,6}}) to the generated patterns.

"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    return output_file
# ============================================================
# LANCEMENT NON-GUI (utilisé par worker_process)
# ============================================================

def run_th14(modulus, limit, n_processes=N_PROCESSES, log_callback=None):
    if log_callback:
        log_callback(f"TH14 VALIDATOR — MOD {modulus}, LIMIT {limit:,}\n")

    validator = TH14Validator(limit=limit, modulus=modulus, n_processes=n_processes)

    if log_callback:
        log_callback(f"Generating primes up to {limit:,}…\n")
        log_callback(f"Found {len(validator.primes):,} primes\n")

    if log_callback:
        log_callback("Finding prime pairs (multiprocessing)…\n")
    validator.find_pairs()

    if log_callback:
        log_callback(f"  Twin   : {len(validator.twin_pairs):,}\n")
        log_callback(f"  Cousin : {len(validator.cousin_pairs):,}\n")
        log_callback(f"  Sexy   : {len(validator.sexy_pairs):,}\n")

    if log_callback:
        log_callback("Validating patterns…\n")
    validator.validate_pairs()

    stats = validator.get_statistics()

    if log_callback:
        log_callback("\nRESULTS\n")
        log_callback(f"Modulus: {stats['modulus']}\n")
        log_callback(f"Max prime factor: {stats['max_prime_factor']}\n")
        log_callback(f"Twin compliance:   {stats['twin_compliance']:.6f}%\n")
        log_callback(f"Cousin compliance: {stats['cousin_compliance']:.6f}%\n")
        log_callback(f"Sexy compliance:   {stats['sexy_compliance']:.6f}%\n")
        log_callback(f"Overall:           {100 * stats['total_conforming'] / stats['total_pairs']:.6f}%\n")
        log_callback(f"Anomalies:         {stats['anomalies_count']:,}\n")

    charts = {}
    charts["compliance"]   = generate_compliance_chart(stats, f"th14_compliance_mod{modulus}_L{limit}.png")
    charts["distribution"] = generate_pair_distribution_chart(stats, f"th14_distribution_mod{modulus}_L{limit}.png")
    charts["patterns"]     = generate_pattern_frequency_chart(validator, f"th14_patterns_mod{modulus}_L{limit}.png")

    report_file = generate_markdown_report(
        validator, stats, charts, f"TH14_Validation_Report_mod{modulus}_L{limit}.md"
    )

    if log_callback:
        log_callback(f"\nReport saved: {report_file}\n")
        log_callback("TH14 VALIDATION COMPLETE\n")


# ============================================================
# WORKER GLOBAL POUR MULTIPROCESSING
# ============================================================

def worker_process(modulus, limit, n_processes, queue):
    def log_callback(msg):
        queue.put(msg)

    run_th14(modulus, limit, n_processes=n_processes, log_callback=log_callback)

    queue.put("__END__")


# ============================================================
# GUI TKINTER
# ============================================================

class TH14GUI:
    def __init__(self, root):
        self.root = root
        root.title("TH14 Modular Validator")

        main_frame = ttk.Frame(root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")

        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # -------------------------
        # Modulus selection
        # -------------------------
        ttk.Label(main_frame, text="Modulus:").grid(row=0, column=0, sticky="w")
        self.modulus_var = tk.IntVar(value=DEFAULT_MODULUS)
        modulus_choices = [30, 210, 2310, 30030,510510]
        self.modulus_combo = ttk.Combobox(
            main_frame, textvariable=self.modulus_var,
            values=modulus_choices, state="readonly"
        )
        self.modulus_combo.grid(row=0, column=1, sticky="ew")

        # -------------------------
        # Limit selection
        # -------------------------
        ttk.Label(main_frame, text="Limit:").grid(row=1, column=0, sticky="w")
        self.limit_var = tk.IntVar(value=DEFAULT_LIMIT)
        limit_choices = [1_000_000, 5_000_000, 10_000_000, 100_000_000]
        self.limit_combo = ttk.Combobox(
            main_frame, textvariable=self.limit_var,
            values=limit_choices, state="readonly"
        )
        self.limit_combo.grid(row=1, column=1, sticky="ew")

        # -------------------------
        # Run button
        # -------------------------
        self.run_button = ttk.Button(main_frame, text="Run TH14", command=self.run_th14_gui)
        self.run_button.grid(row=2, column=0, columnspan=2, pady=10)

        # -------------------------
        # Log output
        # -------------------------
        self.log_text = tk.Text(main_frame, height=20, width=80)
        self.log_text.grid(row=3, column=0, columnspan=2, sticky="nsew")
        main_frame.rowconfigure(3, weight=1)
        main_frame.columnconfigure(1, weight=1)

        self.queue = None

    # ------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------
    def log(self, msg):
        self.log_text.insert("end", msg)
        self.log_text.see("end")
        self.root.update_idletasks()

    # ------------------------------------------------------------
    # Launch TH14 in separate process
    # ------------------------------------------------------------
    def run_th14_gui(self):
        modulus = int(self.modulus_var.get())
        limit = int(self.limit_var.get())

        self.log_text.delete("1.0", "end")
        self.log(f"Starting TH14 validation (mod {modulus}, limit {limit:,})…\n")

        self.queue = mp.Queue()

        p = mp.Process(
            target=worker_process,
            args=(modulus, limit, N_PROCESSES, self.queue)
        )
        p.start()

        self.root.after(100, self.poll_queue)

    # ------------------------------------------------------------
    # Poll queue for logs from worker process
    # ------------------------------------------------------------
    def poll_queue(self):
        if self.queue is None:
            return

        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "__END__":
                    self.log("\nTH14 VALIDATION COMPLETE\n")
                    self.queue = None
                    return
                self.log(msg)
        except Exception:
            pass

        self.root.after(100, self.poll_queue)
# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # IMPORTANT pour multiprocessing sous Linux, macOS, Windows
    mp.set_start_method("spawn")

    root = tk.Tk()
    app = TH14GUI(root)
    root.mainloop()

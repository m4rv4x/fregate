"""Orchestration benchmarks."""
import requests
import time
import json
from pathlib import Path
from .tasks import get_tasks, TASK_CATEGORIES


REPORT_DIR = Path.home() / ".ollama-benchmark" / "reports"


class BenchmarkRunner:
    def __init__(self, ollama_url=None):
        self.ollama_url = (ollama_url or "http://localhost:11434").rstrip("/")

    def run(self, model, task_filter="all"):
        tasks = get_tasks(task_filter)
        results = {"model": model, "tasks": {}, "timestamp": time.time()}

        for task in tasks:
            print(f"  [{task['category']}] {task['name']}...", end=" ", flush=True)
            start = time.time()
            response = self._query(model, task["prompt"])
            elapsed = time.time() - start
            score = task["evaluator"](response)
            results["tasks"][task["name"]] = {
                "category": task["category"],
                "score": score,
                "time": round(elapsed, 2),
                "response_len": len(response),
            }
            print(f"score={score} ({elapsed:.1f}s)")

        self._save_report(results)
        return results

    def compare(self, models):
        all_results = []
        for model in models:
            print(f"\n[*] Benchmark: {model}")
            results = self.run(model, "all")
            all_results.append(results)
        return all_results

    def list_models(self):
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            models = r.json().get("models", [])
            print(f"Modeles disponibles ({len(models)}):")
            for m in models:
                size_mb = m.get("size", 0) / 1024 / 1024
                print(f"  {m['name']:40s} {size_mb:.0f} MB")
        except Exception as e:
            print(f"[!] Erreur: {e}")

    def show_last_report(self):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        reports = sorted(REPORT_DIR.glob("*.json"), reverse=True)
        if not reports:
            print("[-] Aucun rapport"); return
        with open(reports[0]) as f:
            data = json.load(f)
        print_report(data)

    def _query(self, model, prompt):
        try:
            r = requests.post(f"{self.ollama_url}/api/generate", json={
                "model": model, "prompt": prompt, "stream": False,
            }, timeout=120)
            return r.json().get("response", "")
        except Exception as e:
            return f"ERROR: {e}"

    def _save_report(self, results):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        name = f"bench_{results['model'].replace(':','_')}_{int(results['timestamp'])}.json"
        with open(REPORT_DIR / name, "w") as f:
            json.dump(results, f, indent=2)

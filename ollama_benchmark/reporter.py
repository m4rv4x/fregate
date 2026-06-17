"""Generation scorecard."""


def print_report(results):
    model = results.get("model", "?")
    tasks = results.get("tasks", {})
    print(f"\n{'='*50}")
    print(f"  SCORECARD: {model}")
    print(f"{'='*50}")

    by_cat = {}
    for name, data in tasks.items():
        cat = data.get("category", "other")
        by_cat.setdefault(cat, []).append(data)

    total_score = 0
    total_time = 0
    for cat, items in sorted(by_cat.items()):
        scores = [i["score"] for i in items]
        times = [i["time"] for i in items]
        avg = sum(scores) / len(scores) if scores else 0
        total_score += sum(scores)
        total_time += sum(times)
        print(f"  {cat:12s}  score={avg:.0%}  time={sum(times):.1f}s")

    print(f"  {'TOTAL':12s}  score={total_score}  time={total_time:.1f}s")
    print(f"{'='*50}")


def print_comparison(results_list):
    if not results_list:
        return
    print(f"\n{'='*60}")
    print(f"  COMPARAISON")
    print(f"{'='*60}")

    models = [r["model"] for r in results_list]
    print(f"  {'Modele':30s} {'Score':>8s} {'Temps':>8s}")
    print(f"  {'-'*30} {'-'*8} {'-'*8}")

    for r in results_list:
        tasks = r.get("tasks", {})
        total_score = sum(d["score"] for d in tasks.values())
        total_time = sum(d["time"] for d in tasks.values())
        print(f"  {r['model']:30s} {total_score:>8d} {total_time:>7.1f}s")

    print(f"{'='*60}")

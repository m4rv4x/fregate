"""Definitions des taches de benchmark."""

TASK_CATEGORIES = ["code", "french", "reasoning", "tool_use", "speed"]

BENCHMARK_TASKS = [
    # CODE
    {
        "name": "python_fibonacci",
        "category": "code",
        "prompt": "Ecris une fonction Python fibonacci(n) en une ligne avec memoization.",
        "evaluator": lambda r: 1 if "def fibonacci" in r or "fibonacci =" in r else 0,
    },
    {
        "name": "sql_join",
        "category": "code",
        "prompt": "Ecris une requete SQL qui liste les utilisateurs avec le nombre de commandes.",
        "evaluator": lambda r: 1 if "JOIN" in r.upper() and "COUNT" in r.upper() else 0,
    },
    # FRENCH
    {
        "name": "french_summary",
        "category": "french",
        "prompt": "Resume en 3 phrases en francais: Le cloud computing permet aux entreprises de deleguer leur infrastructure informatique a des fournisseurs tiers.",
        "evaluator": lambda r: 1 if len(r) > 50 and any(c in r.lower() for c in ["cloud", "entreprise", "infrastructure"]) else 0,
    },
    # REASONING
    {
        "name": "logic_syllogism",
        "category": "reasoning",
        "prompt": "Tous les hommes sont mortels. Socrate est un homme. Est-ce que Socrate est mortel? Reponds par oui ou non puis explique.",
        "evaluator": lambda r: 1 if "oui" in r.lower() or "yes" in r.lower() or "mortel" in r.lower() else 0,
    },
    {
        "name": "math_basic",
        "category": "reasoning",
        "prompt": "Calcule: 17 * 23 + 45 / 9 - 12. Donne juste le resultat.",
        "evaluator": lambda r: 1 if "386" in r or "380" in r else 0,
    },
    # TOOL USE
    {
        "name": "json_extraction",
        "category": "tool_use",
        "prompt": 'Extrait les IP de ce texte en JSON array: "Le serveur 192.168.1.1 contacte 10.0.0.5 et 172.16.0.100"',
        "evaluator": lambda r: 1 if "192.168.1.1" in r and "10.0.0.5" in r else 0,
    },
    # SPEED
    {
        "name": "speed_hello",
        "category": "speed",
        "prompt": "Dis bonjour en une phrase.",
        "evaluator": lambda r: 1 if len(r) > 5 else 0,
    },
]


def get_tasks(category="all"):
    if category == "all":
        return BENCHMARK_TASKS
    return [t for t in BENCHMARK_TASKS if t["category"] == category]

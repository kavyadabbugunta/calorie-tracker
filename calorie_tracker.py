#!/usr/bin/env python3
"""
Diet & Calorie Tracking System
------------------------------
Features:
  * Profile setup with BMR / TDEE / daily calorie target (Mifflin-St Jeor)
  * Built-in food database (calories + macros per serving), add your own foods
  * Log meals by date, delete entries
  * Daily summary with progress bar and macro breakdown
  * 7-day report
Data is stored in calorie_data.json next to the script.
Run:  python calorie_tracker.py
"""

import json
import os
from datetime import date, datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calorie_data.json")

MEALS = ["Breakfast", "Lunch", "Dinner", "Snack"]

ACTIVITY_LEVELS = {
    "1": ("Sedentary (little or no exercise)", 1.2),
    "2": ("Lightly active (1-3 days/week)", 1.375),
    "3": ("Moderately active (3-5 days/week)", 1.55),
    "4": ("Very active (6-7 days/week)", 1.725),
}

GOALS = {
    "1": ("Lose weight (about 0.5 kg/week)", -500),
    "2": ("Maintain weight", 0),
    "3": ("Gain weight (about 0.5 kg/week)", 500),
}

MIN_SAFE_CALORIES = {"male": 1500, "female": 1200}

# name: (serving description, calories, protein g, carbs g, fat g)
DEFAULT_FOODS = {
    "idli": ("1 piece", 58, 2, 12, 0.4),
    "dosa (plain)": ("1 piece", 130, 3, 22, 3),
    "chapati": ("1 piece", 104, 3, 18, 3),
    "white rice (cooked)": ("1 cup", 205, 4, 45, 0.4),
    "dal (cooked)": ("1 cup", 230, 18, 40, 1),
    "chicken curry": ("1 cup", 240, 24, 8, 12),
    "paneer": ("100 g", 265, 18, 4, 20),
    "egg (boiled)": ("1 large", 78, 6, 0.6, 5),
    "milk (whole)": ("1 cup", 150, 8, 12, 8),
    "curd / yogurt": ("1 cup", 150, 8, 11, 8),
    "banana": ("1 medium", 105, 1.3, 27, 0.4),
    "apple": ("1 medium", 95, 0.5, 25, 0.3),
    "oats (cooked)": ("1 cup", 160, 6, 28, 3),
    "peanuts": ("30 g", 170, 7, 5, 14),
    "biryani (chicken)": ("1 cup", 290, 14, 38, 9),
    "sambar": ("1 cup", 130, 7, 20, 3),
    "bread (white)": ("1 slice", 75, 2.5, 14, 1),
    "peanut butter": ("1 tbsp", 95, 4, 3, 8),
    "salad (mixed veg)": ("1 bowl", 40, 2, 8, 0.3),
    "tea with milk & sugar": ("1 cup", 60, 1.5, 9, 2),
}


# ------------------------------------------------------------------ storage
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print("Warning: data file unreadable, starting fresh.")
    foods = {k: list(v) for k, v in DEFAULT_FOODS.items()}
    return {"profile": None, "foods": foods, "log": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ------------------------------------------------------------------ input helpers
def ask_float(prompt, lo=None, hi=None):
    while True:
        try:
            val = float(input(prompt).strip())
            if (lo is not None and val < lo) or (hi is not None and val > hi):
                print(f"  Please enter a value between {lo} and {hi}.")
                continue
            return val
        except ValueError:
            print("  Please enter a number.")


def ask_choice(prompt, options):
    while True:
        c = input(prompt).strip().lower()
        if c in options:
            return c
        print(f"  Choose one of: {', '.join(options)}")


def ask_date(prompt="Date (YYYY-MM-DD, Enter for today): "):
    while True:
        raw = input(prompt).strip()
        if not raw:
            return date.today().isoformat()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
        except ValueError:
            print("  Invalid date format.")


# ------------------------------------------------------------------ profile
def calc_targets(p):
    """Mifflin-St Jeor BMR, TDEE, and a target that respects a minimum floor."""
    s = 5 if p["sex"] == "male" else -161
    bmr = 10 * p["weight"] + 6.25 * p["height"] - 5 * p["age"] + s
    tdee = bmr * p["activity"]
    target = tdee + p["adjust"]
    floor = MIN_SAFE_CALORIES[p["sex"]]
    floored = target < floor
    target = max(target, floor)
    return round(bmr), round(tdee), round(target), floored


def setup_profile(data):
    print("\n--- Profile Setup ---")
    sex = ask_choice("Sex (male/female): ", ["male", "female"])
    age = ask_float("Age (years): ", 15, 100)
    height = ask_float("Height (cm): ", 120, 230)
    weight = ask_float("Weight (kg): ", 30, 300)

    print("\nActivity level:")
    for k, (label, _) in ACTIVITY_LEVELS.items():
        print(f"  {k}. {label}")
    act = ACTIVITY_LEVELS[ask_choice("Choose: ", list(ACTIVITY_LEVELS))][1]

    print("\nGoal:")
    for k, (label, _) in GOALS.items():
        print(f"  {k}. {label}")
    adjust = GOALS[ask_choice("Choose: ", list(GOALS))][1]

    data["profile"] = {"sex": sex, "age": age, "height": height,
                       "weight": weight, "activity": act, "adjust": adjust}
    bmr, tdee, target, floored = calc_targets(data["profile"])
    data["profile"]["target"] = target
    save_data(data)

    print(f"\nBMR (resting burn):   {bmr} kcal")
    print(f"TDEE (maintenance):   {tdee} kcal")
    print(f"Daily target:         {target} kcal")
    if floored:
        print(f"Note: target was raised to the minimum of {MIN_SAFE_CALORIES[sex]} kcal.")
    print("These are estimates. Adjust based on your real-world results.")


# ------------------------------------------------------------------ foods
def list_foods(data):
    print("\n--- Food Database ---")
    for i, (name, v) in enumerate(sorted(data["foods"].items()), 1):
        print(f"{i:>3}. {name:<24} {v[0]:<10} {v[1]:>5} kcal  "
              f"P{v[2]} C{v[3]} F{v[4]}")


def add_food(data):
    print("\n--- Add Custom Food ---")
    name = input("Food name: ").strip().lower()
    if not name:
        return
    serving = input("Serving description (e.g. '1 cup'): ").strip() or "1 serving"
    cal = ask_float("Calories per serving: ", 0, 5000)
    pro = ask_float("Protein (g): ", 0, 500)
    carb = ask_float("Carbs (g): ", 0, 1000)
    fat = ask_float("Fat (g): ", 0, 500)
    data["foods"][name] = [serving, cal, pro, carb, fat]
    save_data(data)
    print(f"Added '{name}'.")


def find_food(data, query):
    query = query.lower().strip()
    if query in data["foods"]:
        return query
    matches = [n for n in data["foods"] if query in n]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    print("  Multiple matches:")
    for i, m in enumerate(matches, 1):
        print(f"   {i}. {m}")
    while True:
        c = input("  Pick a number (0 to cancel): ").strip()
        if c == "0":
            return None
        if c.isdigit() and 1 <= int(c) <= len(matches):
            return matches[int(c) - 1]


# ------------------------------------------------------------------ logging
def log_meal(data):
    print("\n--- Log a Meal ---")
    day = ask_date()
    for i, m in enumerate(MEALS, 1):
        print(f"  {i}. {m}")
    meal = MEALS[int(ask_choice("Meal: ", [str(i) for i in range(1, len(MEALS) + 1)])) - 1]

    while True:
        q = input("Food name (search, or Enter to finish): ").strip()
        if not q:
            break
        name = find_food(data, q)
        if not name:
            print("  Not found. Use 'Add custom food' from the menu first.")
            continue
        serving, cal, pro, carb, fat = data["foods"][name]
        n = ask_float(f"  How many servings of '{name}' ({serving})? ", 0.1, 50)
        entry = {
            "date": day, "meal": meal, "food": name, "servings": n,
            "calories": round(cal * n, 1), "protein": round(pro * n, 1),
            "carbs": round(carb * n, 1), "fat": round(fat * n, 1),
        }
        data["log"].append(entry)
        save_data(data)
        print(f"  Logged {entry['calories']} kcal.")


def day_entries(data, day):
    return [e for e in data["log"] if e["date"] == day]


def progress_bar(value, goal, width=30):
    ratio = min(value / goal, 1.0) if goal else 0
    filled = int(ratio * width)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {value / goal * 100:.0f}%" if goal else ""


def view_day(data, day=None):
    day = day or ask_date()
    entries = day_entries(data, day)
    print(f"\n=== {day} ===")
    if not entries:
        print("No entries.")
        return
    for meal in MEALS:
        items = [e for e in entries if e["meal"] == meal]
        if items:
            print(f"\n{meal} ({sum(e['calories'] for e in items):.0f} kcal)")
            for e in items:
                print(f"  - {e['food']} x{e['servings']:g}: {e['calories']:.0f} kcal")

    total = sum(e["calories"] for e in entries)
    pro = sum(e["protein"] for e in entries)
    carb = sum(e["carbs"] for e in entries)
    fat = sum(e["fat"] for e in entries)
    print(f"\nTotal: {total:.0f} kcal | Protein {pro:.0f} g | Carbs {carb:.0f} g | Fat {fat:.0f} g")

    macro_kcal = pro * 4 + carb * 4 + fat * 9
    if macro_kcal:
        print(f"Macro split: P {pro*4/macro_kcal*100:.0f}% / "
              f"C {carb*4/macro_kcal*100:.0f}% / F {fat*9/macro_kcal*100:.0f}%")

    if data["profile"]:
        target = data["profile"]["target"]
        print(progress_bar(total, target), f"of {target} kcal")
        diff = target - total
        print(f"{abs(diff):.0f} kcal {'remaining' if diff >= 0 else 'over target'}")


def delete_entry(data):
    day = ask_date()
    entries = day_entries(data, day)
    if not entries:
        print("No entries for that day.")
        return
    for i, e in enumerate(entries, 1):
        print(f"  {i}. {e['meal']}: {e['food']} x{e['servings']:g} ({e['calories']:.0f} kcal)")
    c = input("Number to delete (Enter to cancel): ").strip()
    if c.isdigit() and 1 <= int(c) <= len(entries):
        data["log"].remove(entries[int(c) - 1])
        save_data(data)
        print("Deleted.")


def weekly_report(data):
    print("\n--- Last 7 Days ---")
    target = data["profile"]["target"] if data["profile"] else None
    totals = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        t = sum(e["calories"] for e in day_entries(data, d))
        totals.append(t)
        bar = "#" * int(t / 100)
        flag = ""
        if target and t:
            flag = "  (over)" if t > target else ""
        print(f"{d}  {t:>6.0f} kcal  {bar}{flag}")
    logged = [t for t in totals if t > 0]
    if logged:
        print(f"\nAverage on logged days: {sum(logged) / len(logged):.0f} kcal "
              f"({len(logged)}/7 days logged)")
        if target:
            print(f"Daily target: {target} kcal")


# ------------------------------------------------------------------ main
MENU = """
===== Diet & Calorie Tracker =====
 1. Set up / update profile
 2. Log a meal
 3. View a day
 4. 7-day report
 5. Browse food database
 6. Add custom food
 7. Delete a log entry
 0. Exit
"""


def main():
    data = load_data()
    if not data["profile"]:
        print("Welcome! Let's set up your profile first.")
        setup_profile(data)

    actions = {
        "1": setup_profile, "2": log_meal, "3": view_day, "4": weekly_report,
        "5": list_foods, "6": add_food, "7": delete_entry,
    }
    while True:
        print(MENU)
        choice = input("Choose: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        action = actions.get(choice)
        if action:
            action(data)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")

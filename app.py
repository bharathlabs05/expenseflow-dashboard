
from flask import Flask, render_template, request, redirect, url_for, flash
import json
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "expenseflow-local-secret-key"

DATA_FILE = Path(__file__).with_name("expenses.json")

CATEGORIES = [
    "Food", "Transport", "Shopping",
    "Bills", "Education", "Other"
]


def load_expenses():
    """Load saved expenses from JSON."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_expenses(expenses):
    """Save expenses to JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(expenses, file, indent=4)


def calculate_total(expenses):
    """Calculate total spending."""
    return sum(float(expense["amount"]) for expense in expenses)


def next_expense_id(expenses):
    """Generate a unique expense ID."""
    return max(
        (expense.get("id", 0) for expense in expenses),
        default=0
    ) + 1


@app.route("/")
def dashboard():
    expenses = load_expenses()
    total_spent = calculate_total(expenses)
    expense_count = len(expenses)

    category_totals = {}

    for expense in expenses:
        category = expense["category"]
        amount = float(expense["amount"])
        category_totals[category] = (
            category_totals.get(category, 0) + amount
        )

    return render_template(
        "index.html",
        total_spent=total_spent,
        expense_count=expense_count,
        average_expense=(
            total_spent / expense_count if expense_count else 0
        ),
        today=date.today().isoformat(),
        all_expenses=expenses,
        category_totals=category_totals
    )


@app.route("/find")
def find_expenses():
    expenses = load_expenses()
    query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "All")

    if selected_category not in CATEGORIES and selected_category != "All":
        selected_category = "All"

    filtered_expenses = []

    for expense in expenses:
        matches_search = query.casefold() in expense["title"].casefold()
        matches_category = (
            selected_category == "All"
            or expense["category"] == selected_category
        )

        if matches_search and matches_category:
            filtered_expenses.append(expense)

    return render_template(
        "find.html",
        expenses=filtered_expenses,
        query=query,
        selected_category=selected_category,
        categories=CATEGORIES
    )


@app.route("/add", methods=["POST"])
def add_expense():
    title = request.form.get("title", "").strip()
    amount_text = request.form.get("amount", "").strip()
    category = request.form.get("category", "Other")
    expense_date = request.form.get("expense_date", "")

    # Validate description.
    if not title:
        flash("Please enter an expense description.", "error")
        return redirect(url_for("dashboard"))

    if len(title) > 100:
        flash("Description must be 100 characters or fewer.", "error")
        return redirect(url_for("dashboard"))

    # Validate amount.
    try:
        amount = round(float(amount_text), 2)
    except (ValueError, TypeError):
        flash("Please enter a valid amount.", "error")
        return redirect(url_for("dashboard"))

    if not (0 < amount < 1000000000):
        flash("Amount must be greater than ₹0.", "error")
        return redirect(url_for("dashboard"))

    # Validate date.
    try:
        if not expense_date:
            expense_date = date.today().isoformat()
        else:
            date.fromisoformat(expense_date)
    except ValueError:
        flash("Please select a valid date.", "error")
        return redirect(url_for("dashboard"))

    # Validate category.
    if category not in CATEGORIES:
        flash("Please select a valid category.", "error")
        return redirect(url_for("dashboard"))

    expenses = load_expenses()

    expenses.append({
        "id": next_expense_id(expenses),
        "title": title,
        "amount": amount,
        "category": category,
        "date": expense_date
    })

    try:
        save_expenses(expenses)
    except OSError:
        flash("Could not save the expense. Please try again.", "error")
        return redirect(url_for("dashboard"))

    flash(f"Expense '{title}' added successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    expenses = load_expenses()

    remaining_expenses = [
        expense for expense in expenses
        if expense.get("id") != expense_id
    ]

    if len(remaining_expenses) == len(expenses):
        flash("Expense not found.", "error")
    else:
        try:
            save_expenses(remaining_expenses)
            flash("Expense deleted successfully.", "success")
        except OSError:
            flash("Could not delete the expense. Please try again.", "error")

    # Return to Find Expenses when deletion came from that page.
    if request.referrer and "/find" in request.referrer:
        return redirect(url_for("find_expenses"))

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)

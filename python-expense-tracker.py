
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import date, datetime
import os

APP_NAME = "Personal Expense Tracker"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "expense_tracker.db")

CATEGORIES = [
    "Food", "Transport", "Shopping", "Bills", "Education",
    "Health", "Entertainment", "Salary", "Freelance", "Other"
]


class ExpenseTracker:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1150x720")
        self.root.minsize(950, 620)

        self.dark_mode = False
        self.selected_id = None
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="All")
        self.month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        self.type_var = tk.StringVar(value="Expense")
        self.category_var = tk.StringVar(value="Food")
        self.amount_var = tk.StringVar()
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.description_var = tk.StringVar()
        self.budget_var = tk.StringVar(value="0")

        self.conn = sqlite3.connect(DB_FILE)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT DEFAULT ''
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)
        self.conn.commit()

        self.load_budget()
        self.setup_style()
        self.build_ui()
        self.refresh_table()
        self.update_dashboard()

        self.search_var.trace_add(
            "write", lambda *_: self.refresh_table()
        )

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def setup_style(self):
        self.bg = "#F3F5F9" if not self.dark_mode else "#171923"
        self.card = "#FFFFFF" if not self.dark_mode else "#242735"
        self.fg = "#202938" if not self.dark_mode else "#F2F4F8"
        self.muted = "#697586" if not self.dark_mode else "#A9B0C0"
        self.accent = "#6558D3"
        self.border = "#DCE1EA" if not self.dark_mode else "#3A4051"

        self.root.configure(bg=self.bg)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=self.card,
            foreground=self.fg,
            fieldbackground=self.card,
            rowheight=32,
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=self.bg,
            foreground=self.fg,
            font=("Segoe UI", 10, "bold"),
            padding=9
        )
        style.map(
            "Treeview",
            background=[("selected", self.accent)],
            foreground=[("selected", "#FFFFFF")]
        )
        style.configure(
            "TCombobox",
            padding=6
        )

    def build_ui(self):
        self.main = tk.Frame(self.root, bg=self.bg)
        self.main.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self.main, bg=self.card, padx=22, pady=15)
        header.pack(fill="x")

        tk.Label(
            header, text="Personal Expense Tracker",
            font=("Segoe UI", 19, "bold"),
            bg=self.card, fg=self.fg
        ).pack(side="left")

        tk.Button(
            header, text="Switch Theme",
            command=self.toggle_theme,
            bg=self.accent, fg="white",
            activebackground="#5144BD",
            activeforeground="white",
            relief="flat", padx=14, pady=8,
            cursor="hand2"
        ).pack(side="right")

        # Dashboard cards
        self.stats_frame = tk.Frame(self.main, bg=self.bg)
        self.stats_frame.pack(fill="x", padx=18, pady=16)

        self.income_label = self.create_stat_card(
            self.stats_frame, "TOTAL INCOME", "0.00", "#16875B"
        )
        self.expense_label = self.create_stat_card(
            self.stats_frame, "TOTAL EXPENSES", "0.00", "#D94F55"
        )
        self.balance_label = self.create_stat_card(
            self.stats_frame, "BALANCE", "0.00", self.accent
        )
        self.budget_label = self.create_stat_card(
            self.stats_frame, "BUDGET LEFT", "0.00", "#C18420"
        )

        # Content area
        content = tk.Frame(self.main, bg=self.bg)
        content.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        # Transaction form
        self.form = tk.LabelFrame(
            content, text=" Add Transaction ",
            bg=self.card, fg=self.fg,
            font=("Segoe UI", 11, "bold"),
            padx=14, pady=12
        )
        self.form.pack(side="left", fill="y", padx=(0, 14))

        self.add_form_field("Type", 0)
        self.type_box = ttk.Combobox(
            self.form, textvariable=self.type_var,
            values=["Expense", "Income"],
            state="readonly", width=23
        )
        self.type_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.type_box.bind("<<ComboboxSelected>>", self.on_type_change)

        self.add_form_field("Amount", 2)
        self.amount_entry = tk.Entry(
            self.form, textvariable=self.amount_var,
            font=("Segoe UI", 10), relief="solid", bd=1
        )
        self.amount_entry.grid(
            row=3, column=0, sticky="ew", pady=(0, 10), ipady=6
        )

        self.add_form_field("Category", 4)
        self.category_box = ttk.Combobox(
            self.form, textvariable=self.category_var,
            values=CATEGORIES, state="readonly", width=23
        )
        self.category_box.grid(
            row=5, column=0, sticky="ew", pady=(0, 10)
        )

        self.add_form_field("Date (YYYY-MM-DD)", 6)
        self.date_entry = tk.Entry(
            self.form, textvariable=self.date_var,
            font=("Segoe UI", 10), relief="solid", bd=1
        )
        self.date_entry.grid(
            row=7, column=0, sticky="ew", pady=(0, 10), ipady=6
        )

        self.add_form_field("Description", 8)
        self.description_entry = tk.Entry(
            self.form, textvariable=self.description_var,
            font=("Segoe UI", 10), relief="solid", bd=1
        )
        self.description_entry.grid(
            row=9, column=0, sticky="ew", pady=(0, 12), ipady=6
        )

        self.save_btn = tk.Button(
            self.form, text="Add Transaction",
            command=self.save_transaction,
            bg=self.accent, fg="white",
            activebackground="#5144BD",
            activeforeground="white",
            relief="flat", pady=9, cursor="hand2"
        )
        self.save_btn.grid(row=10, column=0, sticky="ew", pady=3)

        tk.Button(
            self.form, text="Clear Form",
            command=self.clear_form,
            relief="flat", pady=7, cursor="hand2"
        ).grid(row=11, column=0, sticky="ew", pady=3)

        tk.Button(
            self.form, text="Set Monthly Budget",
            command=self.set_budget,
            relief="flat", pady=7, cursor="hand2"
        ).grid(row=12, column=0, sticky="ew", pady=3)

        self.form.columnconfigure(0, weight=1)

        # Transactions table
        self.table_card = tk.Frame(content, bg=self.card, padx=14, pady=12)
        self.table_card.pack(side="left", fill="both", expand=True)

        tk.Label(
            self.table_card, text="Transactions",
            font=("Segoe UI", 14, "bold"),
            bg=self.card, fg=self.fg
        ).pack(anchor="w", pady=(0, 10))

        filters = tk.Frame(self.table_card, bg=self.card)
        filters.pack(fill="x", pady=(0, 10))

        self.search_entry = tk.Entry(
            filters, textvariable=self.search_var,
            font=("Segoe UI", 10), relief="solid", bd=1
        )
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.search_entry.insert(0, "")

        self.filter_box = ttk.Combobox(
            filters, textvariable=self.filter_var,
            values=["All", "Income", "Expense"],
            state="readonly", width=10
        )
        self.filter_box.pack(side="left", padx=(8, 0))
        self.filter_box.bind(
            "<<ComboboxSelected>>", lambda _event: self.refresh_table()
        )

        columns = ("date", "type", "category", "amount", "description")
        self.tree = ttk.Treeview(
            self.table_card, columns=columns,
            show="headings", selectmode="browse"
        )
        headings = {
            "date": ("Date", 95),
            "type": ("Type", 75),
            "category": ("Category", 100),
            "amount": ("Amount", 95),
            "description": ("Description", 150)
        }
        for col, (heading, width) in headings.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=60)

        scrollbar = ttk.Scrollbar(
            self.table_card, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        actions = tk.Frame(self.main, bg=self.bg)
        actions.pack(fill="x", padx=18, pady=(0, 14))

        self.action_button(actions, "Update Selected", self.update_transaction)
        self.action_button(actions, "Delete Selected", self.delete_transaction)
        self.action_button(actions, "Export CSV", self.export_csv)
        self.action_button(actions, "Show All", self.show_all)

        self.status = tk.Label(
            self.main, text="Ready",
            bg=self.bg, fg=self.muted,
            font=("Segoe UI", 9), anchor="w"
        )
        self.status.pack(fill="x", padx=20, pady=(0, 8))

    def create_stat_card(self, parent, title, value, color):
        card = tk.Frame(
            parent, bg=self.card, padx=16, pady=13,
            highlightbackground=self.border, highlightthickness=1
        )
        card.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(
            card, text=title, bg=self.card, fg=self.muted,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        label = tk.Label(
            card, text=value, bg=self.card, fg=color,
            font=("Segoe UI", 17, "bold")
        )
        label.pack(anchor="w", pady=(5, 0))
        return label

    def add_form_field(self, text, row):
        tk.Label(
            self.form, text=text,
            bg=self.card, fg=self.fg,
            font=("Segoe UI", 9)
        ).grid(row=row, column=0, sticky="w", pady=(2, 4))

    def action_button(self, parent, text, command):
        tk.Button(
            parent, text=text, command=command,
            bg=self.card, fg=self.fg,
            activebackground=self.accent,
            activeforeground="white",
            relief="flat", padx=15, pady=9,
            cursor="hand2"
        ).pack(side="left", padx=(0, 8))

    def on_type_change(self, _event=None):
        if self.type_var.get() == "Income":
            self.category_var.set("Salary")
        else:
            self.category_var.set("Food")

    def load_budget(self):
        row = self.conn.execute(
            "SELECT setting_value FROM settings WHERE setting_key='monthly_budget'"
        ).fetchone()
        if row:
            self.budget_var.set(row[0])

    def set_budget(self):
        value = self.ask_budget_value()
        if value is None:
            return
        try:
            amount = float(value)
            if amount < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Budget", "Enter a valid non-negative amount.")
            return

        self.budget_var.set(str(amount))
        self.conn.execute(
            "INSERT OR REPLACE INTO settings(setting_key, setting_value) VALUES (?, ?)",
            ("monthly_budget", str(amount))
        )
        self.conn.commit()
        self.update_dashboard()
        self.status.config(text="Monthly budget saved.")

    def ask_budget_value(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Monthly Budget")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.card)
        dialog.resizable(False, False)

        tk.Label(
            dialog, text="Enter monthly expense budget:",
            bg=self.card, fg=self.fg
        ).pack(padx=20, pady=(20, 8))

        var = tk.StringVar(value=self.budget_var.get())
        entry = tk.Entry(dialog, textvariable=var, width=22)
        entry.pack(padx=20, pady=5)
        entry.focus_set()

        result = {"value": None}

        def submit():
            result["value"] = var.get().strip()
            dialog.destroy()

        tk.Button(
            dialog, text="Save", command=submit,
            bg=self.accent, fg="white", relief="flat", padx=16, pady=6
        ).pack(pady=15)

        dialog.bind("<Return>", lambda _e: submit())
        self.root.wait_window(dialog)
        return result["value"]

    def validate_form(self):
        try:
            amount = float(self.amount_var.get().strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Amount", "Enter an amount greater than zero."
            )
            return None

        try:
            datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(
                "Invalid Date", "Use the date format YYYY-MM-DD."
            )
            return None

        category = self.category_var.get().strip()
        if not category:
            messagebox.showerror("Missing Category", "Select a category.")
            return None

        return (
            self.date_var.get().strip(),
            self.type_var.get(),
            category,
            amount,
            self.description_var.get().strip()
        )

    def save_transaction(self):
        data = self.validate_form()
        if data is None:
            return

        self.conn.execute("""
            INSERT INTO transactions
            (transaction_date, transaction_type, category, amount, description)
            VALUES (?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()

        self.clear_form()
        self.refresh_table()
        self.update_dashboard()
        self.status.config(text="Transaction added successfully.")

    def update_transaction(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Select Transaction", "Select a transaction from the table first."
            )
            return

        data = self.validate_form()
        if data is None:
            return

        self.conn.execute("""
            UPDATE transactions
            SET transaction_date=?, transaction_type=?, category=?,
                amount=?, description=?
            WHERE id=?
        """, (*data, self.selected_id))
        self.conn.commit()

        self.clear_form()
        self.refresh_table()
        self.update_dashboard()
        self.status.config(text="Transaction updated successfully.")

    def delete_transaction(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Select Transaction", "Select a transaction to delete."
            )
            return

        if not messagebox.askyesno(
            "Confirm Delete", "Are you sure you want to delete this transaction?"
        ):
            return

        self.conn.execute(
            "DELETE FROM transactions WHERE id=?", (self.selected_id,)
        )
        self.conn.commit()
        self.clear_form()
        self.refresh_table()
        self.update_dashboard()
        self.status.config(text="Transaction deleted.")

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return

        self.selected_id = int(selection[0])
        row = self.conn.execute("""
            SELECT transaction_date, transaction_type, category, amount, description
            FROM transactions WHERE id=?
        """, (self.selected_id,)).fetchone()

        if row:
            self.date_var.set(row[0])
            self.type_var.set(row[1])
            self.category_var.set(row[2])
            self.amount_var.set(str(row[3]))
            self.description_var.set(row[4] or "")
            self.save_btn.config(text="Add Transaction")
            self.status.config(text=f"Selected transaction #{self.selected_id}")

    def clear_form(self):
        self.selected_id = None
        self.type_var.set("Expense")
        self.category_var.set("Food")
        self.amount_var.set("")
        self.date_var.set(date.today().isoformat())
        self.description_var.set("")
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def refresh_table(self):
        if not hasattr(self, "tree"):
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        query = """
            SELECT id, transaction_date, transaction_type, category, amount, description
            FROM transactions WHERE 1=1
        """
        params = []

        filter_type = self.filter_var.get()
        if filter_type in ("Income", "Expense"):
            query += " AND transaction_type=?"
            params.append(filter_type)

        search = self.search_var.get().strip()
        if search:
            query += """
                AND (category LIKE ? OR description LIKE ?
                     OR transaction_type LIKE ? OR transaction_date LIKE ?)
            """
            term = f"%{search}%"
            params.extend([term, term, term, term])

        query += " ORDER BY transaction_date DESC, id DESC"

        for row in self.conn.execute(query, params).fetchall():
            transaction_id, tx_date, tx_type, category, amount, description = row
            self.tree.insert(
                "", "end", iid=str(transaction_id),
                values=(
                    tx_date, tx_type, category,
                    f"{amount:,.2f}", description or ""
                )
            )

    def update_dashboard(self):
        today_month = date.today().strftime("%Y-%m")
        rows = self.conn.execute("""
            SELECT transaction_type, amount
            FROM transactions
            WHERE substr(transaction_date, 1, 7)=?
        """, (today_month,)).fetchall()

        income = sum(amount for kind, amount in rows if kind == "Income")
        expenses = sum(amount for kind, amount in rows if kind == "Expense")
        balance = income - expenses

        try:
            budget = float(self.budget_var.get() or 0)
        except ValueError:
            budget = 0

        budget_left = budget - expenses

        self.income_label.config(text=f"{income:,.2f}")
        self.expense_label.config(text=f"{expenses:,.2f}")
        self.balance_label.config(text=f"{balance:,.2f}")
        self.budget_label.config(text=f"{budget_left:,.2f}")

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export Transactions",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="expense_report.csv"
        )
        if not path:
            return

        rows = self.conn.execute("""
            SELECT transaction_date, transaction_type, category, amount, description
            FROM transactions ORDER BY transaction_date DESC
        """).fetchall()

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["Date", "Type", "Category", "Amount", "Description"])
                writer.writerows(rows)
            messagebox.showinfo(
                "Export Complete", f"Transactions exported successfully:\n{path}"
            )
            self.status.config(text="CSV export completed.")
        except OSError as exc:
            messagebox.showerror("Export Error", str(exc))

    def show_all(self):
        self.search_var.set("")
        self.filter_var.set("All")
        self.refresh_table()
        self.status.config(text="Showing all transactions.")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.setup_style()

        # Rebuild widgets so every part follows the selected theme.
        for widget in self.main.winfo_children():
            widget.destroy()

        self.build_ui()
        self.refresh_table()
        self.update_dashboard()

    def close_app(self):
        self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ExpenseTracker(root)
    root.mainloop()


import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
from datetime import datetime
import csv

# Mapping for date formats
date_format_map = {
    'YYYY-MM-DD': '%Y-%m-%d',
    'MM/DD/YYYY': '%m/%d/%Y',
    'DD.MM.YYYY': '%d.%m.%Y',
}

class ExpenseTracker:
    DB_FILE = 'expenses.db'

    def __init__(self, root):
        self.root = root
        self.root.title('Personal Expense Tracker')

        # Preferences defaults
        self.date_format = 'YYYY-MM-DD'
        self.currency_symbol = '$'

        # Database setup
        self.conn = sqlite3.connect(self.DB_FILE)
        self.cursor = self.conn.cursor()
        self._init_db()

        # Build UI
        self._build_ui()
        self._load_expenses()

    def _init_db(self):
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS expenses (
               id INTEGER PRIMARY KEY,
               date TEXT,
               description TEXT,
               amount REAL)'''
        )
        self.conn.commit()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # Menu bar
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Load Expenses...', command=self.load_file)
        file_menu.add_command(label='Export to CSV', command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.root.quit)
        menubar.add_cascade(label='File', menu=file_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label='Preferences...', command=self.open_settings)
        menubar.add_cascade(label='Settings', menu=settings_menu)
        self.root.config(menu=menubar)

        # Input row
        ttk.Label(frm, text='Date:').grid(row=0, column=0, sticky=tk.W)
        self.date_var = tk.StringVar(value=datetime.now().strftime(date_format_map[self.date_format]))
        ttk.Entry(frm, textvariable=self.date_var, width=12).grid(row=0, column=1)

        ttk.Label(frm, text='Description:').grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.desc_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.desc_var, width=30).grid(row=0, column=3)

        ttk.Label(frm, text='Amount:').grid(row=0, column=4, sticky=tk.W, padx=(10,0))
        self.amount_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.amount_var, width=10).grid(row=0, column=5)

        ttk.Button(frm, text='Add Expense', command=self.add_expense).grid(row=0, column=6, padx=(10,0))

        # Expense list
        cols = ('id', 'date', 'description', 'amount')
        self.tree = ttk.Treeview(frm, columns=cols, show='headings')
        for col, width in [('date',100), ('description',250), ('amount',100)]:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width, anchor=tk.W)
        self.tree.column('id', width=0, stretch=False)
        self.tree.grid(row=1, column=0, columnspan=7, pady=10, sticky='nsew')

        sb = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.grid(row=1, column=7, sticky='ns')

        # Controls & total
        ctrl = ttk.Frame(frm)
        ctrl.grid(row=2, column=0, columnspan=7, sticky='w')
        ttk.Button(ctrl, text='Delete Selected', command=self.delete_expense).pack(side=tk.LEFT)
        self.total_var = tk.StringVar()
        ttk.Label(frm, textvariable=self.total_var, font=('Segoe UI',12,'bold')).grid(row=2, column=6, sticky=tk.E)

        frm.rowconfigure(1, weight=1)
        frm.columnconfigure(3, weight=1)

    def _load_expenses(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        self.cursor.execute('SELECT id, date, description, amount FROM expenses ORDER BY date')
        for eid, d, desc, amt in self.cursor.fetchall():
            try:
                dt = datetime.strptime(d, '%Y-%m-%d')
                disp_date = dt.strftime(date_format_map[self.date_format])
            except:
                disp_date = d
            disp_amt = f'{self.currency_symbol}{amt:.2f}'
            self.tree.insert('', tk.END, values=(eid, disp_date, desc, disp_amt))
        self._update_total()

    def add_expense(self):
        d = self.date_var.get().strip()
        try:
            dt = datetime.strptime(d, date_format_map[self.date_format])
            sd = dt.strftime('%Y-%m-%d')
        except ValueError:
            return messagebox.showerror('Invalid Date', 'Match the selected format.')
        desc = self.desc_var.get().strip()
        try:
            amt = float(self.amount_var.get().strip())
        except ValueError:
            return messagebox.showerror('Invalid Amount', 'Enter a number.')
        if not desc:
            return messagebox.showerror('Missing Data', 'Description required.')
        self.cursor.execute('INSERT INTO expenses (date, description, amount) VALUES (?,?,?)', (sd, desc, amt))
        self.conn.commit()
        self._load_expenses()
        self.desc_var.set('')
        self.amount_var.set('')

    def delete_expense(self):
        sel = self.tree.selection()
        if sel:
            eid = self.tree.item(sel)['values'][0]
            self.cursor.execute('DELETE FROM expenses WHERE id=?', (eid,))
            self.conn.commit()
            self._load_expenses()

    def _update_total(self):
        total = self.cursor.execute('SELECT SUM(amount) FROM expenses').fetchone()[0] or 0.0
        self.total_var.set(f'Total: {self.currency_symbol}{total:.2f}')

    def load_file(self):
        path = filedialog.askopenfilename(
            initialdir=os.path.expanduser('~/Desktop'),
            title='Select Expense CSV',
            filetypes=[('CSV files','*.csv')]
        )
        if not path: return
        imported = 0
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                try:
                    self.cursor.execute(
                        'INSERT INTO expenses (date, description, amount) VALUES (?,?,?)',
                        (row['Date'], row['Description'], float(row['Amount']))
                    )
                    imported += 1
                except:
                    pass
        self.conn.commit()
        if imported:
            self._load_expenses()
            messagebox.showinfo('Loaded', f'Imported {imported} entries.')
        else:
            messagebox.showwarning('No Data', 'No valid entries found.')

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files','*.csv')])
        if path:
            rows = self.cursor.execute('SELECT date, description, amount FROM expenses ORDER BY date').fetchall()
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Currency', self.currency_symbol])
                writer.writerow(['Date','Description','Amount'])
                for d,desc,amt in rows:
                    writer.writerow([d, desc, f'{self.currency_symbol}{amt:.2f}'])
            messagebox.showinfo('Exported', f'Saved to {os.path.basename(path)}')

    def open_settings(self):
        SettingsDialog(self)

    def __del__(self):
        self.conn.close()

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent.root)
        self.parent = parent
        self.title('Preferences')
        self.geometry('300x150')
        self.transient(parent.root)
        # Center
        px, py = parent.root.winfo_rootx(), parent.root.winfo_rooty()
        self.geometry(f'+{px+50}+{py+50}')

        # Date Format
        ttk.Label(self, text='Date Format:').grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.date_fmt = tk.StringVar(value=parent.date_format)
        ttk.Combobox(self, textvariable=self.date_fmt, state='readonly',
                     values=list(date_format_map.keys())).grid(row=0, column=1, pady=5)

        # Currency
        ttk.Label(self, text='Currency Symbol:').grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.currency = tk.StringVar(value=parent.currency_symbol)
        ttk.Entry(self, textvariable=self.currency, width=5).grid(row=1, column=1)

        # Save
        ttk.Button(self, text='Save', command=self.apply_and_close).grid(row=2, column=1, pady=10, sticky=tk.E)

    def apply_and_close(self):
        self.parent.date_format = self.date_fmt.get()
        self.parent.currency_symbol = self.currency.get()
        self.parent._load_expenses()
        self.parent._update_total()
        self.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    ExpenseTracker(root)
    root.mainloop()

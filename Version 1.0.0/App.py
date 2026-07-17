import database
import tkinter as tk
from tkinter import simpledialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import calendar
from datetime import date

BG_COLOR = "navy"
TEXT_COLOR = "white"
checkbox_vars = {}

pending_changes = {}

today = date.today()
current_month = today.month
current_year = today.year

root = tk.Tk()
database.create_database()
root.title("Task Planner")
width = root.winfo_screenwidth()
height = root.winfo_screenheight()
root.geometry(f"{width}x{height}")

top_frame = tk.Frame(root, height=int(height * 0.38))
top_frame.pack(side="top", fill="x")
top_frame.pack_propagate(False)

canvas = tk.Canvas(root, bg="#eeeeee", highlightthickness=0)
canvas.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")
canvas.configure(yscrollcommand=scrollbar.set)

scroll_frame = tk.Frame(canvas)
canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=width)

weekly_graph_frame = tk.Frame(top_frame, bg="white")
weekly_graph_frame.place(relx=0, rely=0.1, relwidth=0.35, relheight=0.65)

monthly_graph_frame = tk.Frame(top_frame, bg="white")
monthly_graph_frame.place(relx=0.355, rely=0.1, relwidth=0.4, relheight=0.65)


def get_current_week_range():
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    if current_year == today.year and current_month == today.month:
        current_day = today.day
    else:
        current_day = 1
    week_index = (current_day - 1) // 7
    week_start = week_index * 7 + 1
    week_end = min(week_start + 6, days_in_month)
    return week_start, week_end, week_index + 1


def show_bar_graph():
    # FIX (#weekly-empty / redesign): Weekly Progress now compares WEEKS of the
    # current month against each other (not tasks against each other).
    # Each bar = average completion % across all tasks for that week.
    week_data = database.get_week_comparison(current_month, current_year)
    _, _, current_week_num = get_current_week_range()

    week_labels_list = [f"Week {w}" for w, pct, s, e in week_data]
    weekly_progress = [pct for w, pct, s, e in week_data]
    week_colors = ["#4D3EEF" if w == current_week_num else "#9AA6FF" for w, pct, s, e in week_data]

    # Monthly Progress now compares MONTHS of the current year against each
    # other. Each bar = average completion % across all tasks in that month.
    month_data = database.get_month_comparison(current_year)
    month_labels_list = [calendar.month_abbr[m] for m, pct in month_data]
    monthly_progress = [pct for m, pct in month_data]
    month_colors = ["#FF0000" if m == current_month else "#FF9E9E" for m, pct in month_data]

    for widget in weekly_graph_frame.winfo_children():
        widget.destroy()
    for widget in monthly_graph_frame.winfo_children():
        widget.destroy()

    fig1 = Figure(figsize=(4, 3), dpi=80)
    ax1 = fig1.add_subplot(111)
    ax1.bar(week_labels_list, weekly_progress, color=week_colors)
    ax1.set_ylim(0, 100)
    ax1.set_ylabel("Completion %")
    ax1.set_title(f"Weekly Comparison - {calendar.month_name[current_month]} {current_year}")
    fig1.tight_layout()

    chart1 = FigureCanvasTkAgg(fig1, master=weekly_graph_frame)
    chart1.draw()
    chart1.get_tk_widget().pack(fill="both", expand=True)

    fig2 = Figure(figsize=(5, 3), dpi=80)
    ax2 = fig2.add_subplot(111)
    ax2.bar(month_labels_list, monthly_progress, color=month_colors)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("Completion %")
    ax2.set_title(f"Monthly Comparison - {current_year}")
    fig2.tight_layout()

    chart2 = FigureCanvasTkAgg(fig2, master=monthly_graph_frame)
    chart2.draw()
    chart2.get_tk_widget().pack(fill="both", expand=True)


# FIX (#2): this is the ONLY place that writes pending changes to the DB
# and refreshes the graphs. Checkbox clicks just update local state.
def save_progress():
    global pending_changes
    for (task_id, day), status in pending_changes.items():
        database.update_progress(task_id, day, status)
    pending_changes = {}
    show_bar_graph()


def on_frame_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))


scroll_frame.bind("<Configure>", on_frame_configure)


def on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


canvas.bind_all("<MouseWheel>", on_mousewheel)

task_y = 0
ROW_HEIGHT = 55
START_X = 0.210
DATE_WIDTH = 0.024
BOX_SIZE = 0.014
TOTAL_CALENDAR_WIDTH = DATE_WIDTH * 31

month_labels = []
week_labels = []
date_labels = []


def clear_month_widgets():
    global month_labels, week_labels, date_labels
    for lbl in month_labels:
        lbl.destroy()
    for lbl in week_labels:
        lbl.destroy()
    for lbl in date_labels:
        lbl.destroy()
    month_labels = []
    week_labels = []
    date_labels = []


def clear_task_widgets():
    global task_y
    for widget in scroll_frame.winfo_children():
        widget.destroy()
    task_y = 0
    checkbox_vars.clear()

def select_month(month):
    global current_month, pending_changes

    pending_changes = {}

    current_month = month

    clear_task_widgets()
    draw_calendar_strip()
    load_tasks()
    show_bar_graph()

def draw_calendar_strip():
    clear_month_widgets()

    days_in_month = calendar.monthrange(current_year, current_month)[1]

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    month_width = TOTAL_CALENDAR_WIDTH / 12
    x = START_X

    for i, month in enumerate(months):

        bg = "#4D3EEF" if (i+1) == current_month else BG_COLOR

        btn = tk.Button(
            top_frame,
            text=month,
            font=("Arial",14),
            bg=bg,
            fg=TEXT_COLOR,
            bd=0,
            cursor="hand2",
            command=lambda m=i+1: select_month(m)
        )

        btn.place(
            relx=x,
            rely=0.75,
            relwidth=month_width-0.003,
            relheight=0.08
        )

        month_labels.append(btn)

        x += month_width

    num_weeks = -(-days_in_month // 7)
    week_width = TOTAL_CALENDAR_WIDTH / num_weeks
    x = START_X
    for w in range(1, num_weeks + 1):
        label = tk.Label(top_frame, text=f"Week {w}", font=("Arial", 14), bg=BG_COLOR, fg=TEXT_COLOR)
        label.place(relx=x, rely=0.84, relwidth=week_width - 0.005, relheight=0.08)
        week_labels.append(label)
        x += week_width

    start_x = START_X
    day_width = TOTAL_CALENDAR_WIDTH / 31
    for day in range(1, days_in_month + 1):
        bg = "#4D3EEF" if (current_year == today.year and current_month == today.month and day == today.day) else "white"
        fg = "white" if bg == "#4D3EEF" else "black"
        label = tk.Label(top_frame, text=str(day), font=("Arial", 10), bg=bg, fg=fg)
        label.place(relx=start_x, rely=0.92, relwidth=day_width, relheight=0.08)
        date_labels.append(label)
        start_x += day_width


def add_task():
    global task_y

    task_name = simpledialog.askstring("Add Task", "Enter Task Name:")

    if task_name:
        task_id = database.add_task(task_name, current_month, current_year)
        render_task_row(task_id, task_name)
        show_bar_graph()


def render_task_row(task_id, task_name):
    global task_y

    label = tk.Label(scroll_frame, text=task_name, font=("Arial", 14), bg=BG_COLOR, fg=TEXT_COLOR)
    label.place(relx=0, y=task_y, relwidth=0.2, height=50)

    row_vars = []
    x = START_X

    progress = database.get_progress(task_id)

    for day in range(1, 32):
        var = tk.IntVar()
        for d, status in progress:
            if d == day:
                var.set(status)

        checkbox = tk.Checkbutton(
            scroll_frame, variable=var, indicatoron=False, onvalue=1, offvalue=0,
            bg="white", fg="white", selectcolor="#4D3EEF", activebackground="#dddddd",
            relief="solid", bd=2, highlightbackground="black", highlightthickness=1,
            padx=0, pady=0, font=("Arial", 10, "bold")
        )
        # initialize checkmark text to match stored state
        checkbox.config(text="✓" if var.get() else "")

        # FIX (#2): only update local pending_changes + the checkbox glyph here.
        # No database write and no graph redraw happens on every click anymore.
        def on_toggle(*args, cb=checkbox, v=var, d=day, t_id=task_id):
            cb.config(text="✓" if v.get() else "")
            pending_changes[(t_id, d)] = v.get()

        var.trace_add("write", on_toggle)

        box_x = x + (DATE_WIDTH - BOX_SIZE) / 2
        checkbox.place(relx=box_x, y=task_y + 8, relwidth=BOX_SIZE, height=30)
        row_vars.append(var)
        x += DATE_WIDTH

    checkbox_vars[task_id] = row_vars
    task_y += ROW_HEIGHT
    scroll_frame.config(height=task_y)


def load_tasks():
    tasks = database.get_tasks(current_month, current_year)
    for task_id, task_name in tasks:
        render_task_row(task_id, task_name)


def change_month(delta):
    global current_month, current_year, pending_changes

    # Discard any unsaved checkbox edits before navigating away, since those
    # edits were tied to the previous month's tasks/day grid.
    pending_changes = {}

    current_month += delta
    if current_month > 12:
        current_month = 1
        current_year += 1
    elif current_month < 1:
        current_month = 12
        current_year -= 1

    

    clear_task_widgets()
    draw_calendar_strip()
    load_tasks()
    show_bar_graph()


label = tk.Label(top_frame, text="Weekly Progress", font=("Arial", 14), bg=BG_COLOR, fg=TEXT_COLOR)
label.place(relx=0, rely=0, relwidth=0.35, relheight=0.1)

label = tk.Label(top_frame, text="Monthly Progress", font=("Arial", 14), bg=BG_COLOR, fg=TEXT_COLOR)
label.place(relx=0.355, rely=0, relwidth=0.40, relheight=0.1)

btn = tk.Button(top_frame, text="Save Progress", font=("Segoe UI", 12, "bold"), bg="#FF0000", fg="white",
                bd=0, cursor="hand2", command=save_progress)
btn.place(relx=0.775, rely=0.02, relwidth=0.11, relheight=0.14)

btn = tk.Button(top_frame, text="➕ Add Task", font=("Segoe UI", 12, "bold"), bg="#4D3EEF", fg="white",
                bd=0, cursor="hand2", command=add_task)
btn.place(relx=0.775, rely=0.19, relwidth=0.11, relheight=0.14)

label = tk.Label(top_frame, text="Day Tasks", font=("Arial", 14), bg=BG_COLOR, fg=TEXT_COLOR)
label.place(relx=0, rely=0.75, relwidth=0.2, relheight=0.16)

draw_calendar_strip()
load_tasks()
show_bar_graph()

root.mainloop()
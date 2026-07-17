import sqlite3
import os
import calendar

folder = os.path.join(os.getenv("LOCALAPPDATA"), "TaskPlanner")
os.makedirs(folder, exist_ok=True)
db_path = os.path.join(folder, "taskplanner.db")


def get_connection():
    return sqlite3.connect(db_path)


def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        day INTEGER,
        completed INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


def add_task(task_name, month, year):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO tasks (task_name, month, year) VALUES (?, ?, ?)", (task_name, month, year))
    task_id = cursor.lastrowid

    for day in range(1, 32):
        cursor.execute(
            "INSERT INTO progress (task_id, day, completed) VALUES (?, ?, ?)",
            (task_id, day, 0)
        )

    conn.commit()
    conn.close()
    return task_id


def update_progress(task_id, day, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE progress SET completed = ? WHERE task_id = ? AND day = ?",
        (status, task_id, day)
    )

    conn.commit()
    conn.close()


def get_tasks(month, year):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, task_name FROM tasks WHERE month=? AND year=?", (month, year))
    data = cursor.fetchall()
    conn.close()
    return data


def get_progress(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT day, completed FROM progress WHERE task_id=?", (task_id,))
    data = cursor.fetchall()
    conn.close()
    return data


def get_task_progress(month, year):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT tasks.task_name,
    SUM(progress.completed)
    FROM tasks
    LEFT JOIN progress
    ON tasks.id = progress.task_id
    WHERE tasks.month=? AND tasks.year=?
    GROUP BY tasks.id
    """, (month, year))

    data = cursor.fetchall()
    conn.close()
    return data


def get_week_progress(month, year, week_start_day, week_end_day):
    """
    FIX: The previous version put the day-range filter in the WHERE clause,
    which effectively turns the LEFT JOIN into an INNER JOIN (any progress
    row outside the range gets dropped BEFORE the join result is grouped,
    and if a task's rows don't match, filtering removes rows needed for
    the join to succeed in edge cases, and NULL-completed tasks vanish).

    The day-range condition now lives in the JOIN's ON clause instead,
    so every task still appears in the result (LEFT JOIN preserved),
    with completed sums restricted to the requested day range only.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT tasks.task_name,
    SUM(progress.completed)
    FROM tasks
    LEFT JOIN progress
    ON tasks.id = progress.task_id
    AND progress.day BETWEEN ? AND ?
    WHERE tasks.month=? AND tasks.year=?
    GROUP BY tasks.id
    """, (week_start_day, week_end_day, month, year))

    data = cursor.fetchall()
    conn.close()
    return data


def get_month_comparison(year):
    """
    Returns [(month_number, completion_percentage), ...] for all 12 months
    of the given year. completion_percentage is the average completion
    across ALL tasks that existed in that month (total completed days /
    (task_count * days_in_that_month) * 100). Months with no tasks show 0.
    """
    conn = get_connection()
    cursor = conn.cursor()

    results = []
    for month in range(1, 13):
        days_in_month = calendar.monthrange(year, month)[1]

        cursor.execute("""
        SELECT COUNT(DISTINCT tasks.id), COALESCE(SUM(progress.completed), 0)
        FROM tasks
        LEFT JOIN progress ON tasks.id = progress.task_id
        WHERE tasks.month=? AND tasks.year=?
        """, (month, year))

        task_count, total_completed = cursor.fetchone()
        task_count = task_count or 0

        if task_count > 0:
            percentage = (total_completed / (task_count * days_in_month)) * 100
        else:
            percentage = 0

        results.append((month, percentage))

    conn.close()
    return results


def get_week_comparison(month, year):
    """
    Returns [(week_number, completion_percentage, week_start_day, week_end_day), ...]
    for every week of the given month. completion_percentage is the average
    completion across ALL tasks in that month for that week's days only
    (total completed days in week / (task_count * days_in_week) * 100).
    """
    conn = get_connection()
    cursor = conn.cursor()

    days_in_month = calendar.monthrange(year, month)[1]
    num_weeks = -(-days_in_month // 7)

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE month=? AND year=?", (month, year))
    task_count = cursor.fetchone()[0] or 0

    results = []
    for w in range(num_weeks):
        week_start = w * 7 + 1
        week_end = min(week_start + 6, days_in_month)
        week_days = week_end - week_start + 1

        cursor.execute("""
        SELECT COALESCE(SUM(progress.completed), 0)
        FROM tasks
        LEFT JOIN progress
        ON tasks.id = progress.task_id
        AND progress.day BETWEEN ? AND ?
        WHERE tasks.month=? AND tasks.year=?
        """, (week_start, week_end, month, year))

        total_completed = cursor.fetchone()[0] or 0

        if task_count > 0:
            percentage = (total_completed / (task_count * week_days)) * 100
        else:
            percentage = 0

        results.append((w + 1, percentage, week_start, week_end))

    conn.close()
    return results


def clear_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks")
    cursor.execute("DELETE FROM progress")
    conn.commit()
    conn.close()
from flask import Flask, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_PATH = "/home/piggery/PigSystem/pigdata.db"

def get_latest_readings(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT ts, ambient_temp, humidity, sow_temp, solenoid FROM readings ORDER BY id DESC LIMIT {limit}")
    rows = c.fetchall()
    conn.close()
    # Reverse to show oldest first
    return rows[::-1]

@app.route('/')
def dashboard():
    readings = get_latest_readings()
    return render_template('dashboard.html', readings=readings, now=datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

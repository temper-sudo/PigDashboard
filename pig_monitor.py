import time, os, sqlite3
import board, busio
import adafruit_mlx90614
# import adafruit_sht4x
import adafruit_ds3231
import RPi.GPIO as GPIO
from datetime import datetime

# --- CONFIGURATION ---
DB_PATH = "/home/piggery/PigSystem/pigdata.db"
RELAY_PIN = 18
HOT_THRESHOLD = 35.0     # ambient temp threshold
FEVER_THRESHOLD = 39.5   # sow temp threshold
MIST_DURATION = 5        # seconds 
READ_INTERVAL = 10       # seconds between readings
COOLDOWN_INTERVAL = 60   # seconds between mistings


# --- GPIO SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.LOW)

# --- I2C SETUP ---
i2c = busio.I2C(board.SCL, board.SDA)
mlx = adafruit_mlx90614.MLX90614(i2c)
rtc = adafruit_ds3231.DS3231(i2c)

# --- DATABASE HELPERS ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        ambient_temp REAL,
        humidity REAL,
        sow_temp REAL,
        solenoid INTEGER
    )
    """)
    conn.commit()
    conn.close()

def insert_reading(ts, ambient, hum, sow, sol_on):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO readings (ts, ambient_temp, humidity, sow_temp, solenoid) VALUES (?,?,?,?,?)",
        (ts, ambient, hum, sow, 1 if sol_on else 0)
    )
    conn.commit()
    conn.close()

init_db()
last_mist_time = 0
print("?? Starting Pig Cooling System (with Database)...")
time.sleep(1)

try:
    while True:
        # simulate environment until SHT40 arrives
        ambient_temp = 33.0
        humidity = 60.0

        # read sensors
        sow_temp = mlx.object_temperature
        # When SHT4x arrives:
        # sht = adafruit_sht4x.SHT4x(i2c)
        # ambient_temp, humidity = sht.measurements

        rtc_now = rtc.datetime
        current_time = datetime(*rtc_now[:6]).isoformat(sep=' ')

        # decision logic
        sol_on = False
        now = time.time()
        if ambient_temp >= HOT_THRESHOLD:
            if sow_temp < FEVER_THRESHOLD:
                if now - last_mist_time >= COOLDOWN_INTERVAL:
                    print(f"[{current_time}] Hot ({ambient_temp:.1f} C) - misting")
                    GPIO.output(RELAY_PIN, GPIO.HIGH)
                    time.sleep(MIST_DURATION)
                    GPIO.output(RELAY_PIN, GPIO.LOW)
                    last_mist_time = now
                    sol_on = True
                else:
                    print(f"[{current_time}] Hot but cooldown active")
            else:
                print(f"[{current_time}] Sow fever ({sow_temp:.1f} C) - skip mist")
        else:
            print(f"[{current_time}] Ambient normal ({ambient_temp:.1f} C)")

        # --- Log to database ---
        insert_reading(current_time, ambient_temp, humidity, sow_temp, sol_on)

        os.system("clear")
        print("PIG COOLING SYSTEM DASHBOARD")
        print("=" * 40)
        print(f"Time: {current_time}")
        print(f"Ambient Temp: {ambient_temp:.1f} C")
        print(f"Humidity: {humidity:.1f}%")
        print(f"Sow Temp: {sow_temp:.1f} C")
        print(f"Solenoid: {'ON' if sol_on else 'OFF'}")
        print("=" * 40)

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.cleanup()

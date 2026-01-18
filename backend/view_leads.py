
import sqlite3
import os

# Path to the database
DB_PATH = os.path.join(os.path.dirname(__file__), 'lumina_leads.db')

def view_leads():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at: {DB_PATH}")
        return

    print(f"Connecting to database: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads';")
        if not cursor.fetchone():
             print("Table 'leads' does not exist yet.")
             return

        # Query data
        cursor.execute('SELECT id, name, email, status, created_at, notes FROM leads')
        rows = cursor.fetchall()
        
        if not rows:
            print("No leads found in the database.")
        else:
            print(f"\nFound {len(rows)} leads:")
            print("-" * 80)
            print(f"{'ID':<4} | {'Name':<15} | {'Email':<30} | {'Date':<20}")
            print("-" * 80)
            for row in rows:
                id, name, email, status, created_at, notes = row
                print(f"{id:<4} | {name:<15} | {email:<30} | {created_at:<20}")
                if notes:
                    print(f"     Note: {notes}")
            print("-" * 80)

        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    view_leads()

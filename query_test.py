import psycopg
from dotenv import dotenv_values
env = dotenv_values(".env")
url = env.get("LABEL_GUARDIAN_DATABASE_URL")
print(f"URL: {url}")
if url:
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT dataset, COUNT(*) FROM qa_images WHERE release = 'product' GROUP BY dataset;")
            rows = cur.fetchall()
            print("DB Counts:", rows)

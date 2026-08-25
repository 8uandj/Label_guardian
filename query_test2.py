import psycopg
from dotenv import dotenv_values
env = dotenv_values(".env")
url = env.get("LABEL_GUARDIAN_DATABASE_URL")
if url:
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT source_image_id FROM qa_images WHERE release = 'product' AND dataset = 'nuscenes' LIMIT 10;")
            rows = cur.fetchall()
            for r in rows: print(r[0])

import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres.nrvsbggjlbvnhpxsahcg:JGY%26v78n%40gH%2CQ8p@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres")
    print("Connected ap-southeast-1")
    conn.close()
except Exception as e:
    print("Failed 1:", e)

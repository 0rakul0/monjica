import sqlite3

from config import DB_PATH

QUERIES = {
    "caps": "SELECT COUNT(*) FROM caps",
    "leitos": "SELECT COUNT(*) FROM leitos",
    "srts": "SELECT COUNT(*) FROM srts",
    "municipios_geo": "SELECT COUNT(*) FROM municipios_geo",
}


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        for nome, query in QUERIES.items():
            total = conn.execute(query).fetchone()[0]
            print(f"{nome}: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

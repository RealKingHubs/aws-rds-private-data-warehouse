"""
connect_and_query.py

Connects to the private RDS MySQL instance through an SSH tunnel via the
bastion host, then runs a query against the Interns table.

All connection details are read from environment variables. See
README.md > Configuration for the full list of required variables.

Usage:
    python scripts/connect_and_query.py
"""

import os
import sys

import pymysql
from sshtunnel import SSHTunnelForwarder


def get_required_env(name: str) -> str:
    """Fetch a required environment variable or exit with a clear error."""
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def load_config() -> dict:
    return {
        "ssh_host": get_required_env("BASTION_HOST"),
        "ssh_user": get_required_env("BASTION_USER"),
        "ssh_key_path": os.path.expanduser(get_required_env("SSH_KEY_PATH")),
        "rds_host": get_required_env("RDS_HOST"),
        "rds_port": int(os.environ.get("RDS_PORT", 3306)),
        "rds_user": get_required_env("RDS_USER"),
        "rds_password": get_required_env("RDS_PASSWORD"),
        "rds_db_name": get_required_env("RDS_DB_NAME"),
    }


def fetch_interns(config: dict) -> list:
    """
    Opens an SSH tunnel through the bastion host, connects to RDS through
    that tunnel, and returns all rows from the Interns table.
    """
    with SSHTunnelForwarder(
        (config["ssh_host"], 22),
        ssh_username=config["ssh_user"],
        ssh_pkey=config["ssh_key_path"],
        remote_bind_address=(config["rds_host"], config["rds_port"]),
    ) as tunnel:
        connection = pymysql.connect(
            host="127.0.0.1",
            port=tunnel.local_bind_port,
            user=config["rds_user"],
            password=config["rds_password"],
            database=config["rds_db_name"],
            connect_timeout=10,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT InternID, FirstName, LastName, Email FROM Interns;")
                return cursor.fetchall()
        finally:
            connection.close()


def print_rows(rows: list) -> None:
    if not rows:
        print("No records found in Interns table.")
        return

    header = f"{'ID':<5} {'First Name':<15} {'Last Name':<15} {'Email':<30}"
    print(header)
    print("-" * len(header))
    for row in rows:
        intern_id, first_name, last_name, email = row
        print(f"{intern_id:<5} {first_name:<15} {last_name:<15} {email:<30}")


def main() -> None:
    config = load_config()
    try:
        rows = fetch_interns(config)
    except Exception as error:
        sys.exit(f"Failed to fetch data: {error}")

    print_rows(rows)


if __name__ == "__main__":
    main()

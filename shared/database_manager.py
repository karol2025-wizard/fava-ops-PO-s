import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
import streamlit as st
from typing import List, Dict, Any
from config import secrets

class DatabaseManager:
    def __init__(self):
        self.pool = MySQLConnectionPool(
            pool_name="mypool",
            pool_size=5,
            host=secrets['starship_db_host'],
            port=secrets['starship_db_port'],
            user=secrets['starship_db_user'],
            password=secrets['starship_db_password'],
            database=secrets['starship_db_database']
        )

    def execute_query(self, query: str, values: tuple = None):
        """Execute a query and return the number of affected rows. Raises exception on error."""
        with self.pool.get_connection() as connection:
            with connection.cursor() as cursor:
                try:
                    if values:
                        cursor.execute(query, values)
                    else:
                        cursor.execute(query)
                    connection.commit()
                    return cursor.rowcount
                except mysql.connector.Error as e:
                    connection.rollback()
                    st.error(f"Error executing query: {e}")
                    raise
                except Exception as e:
                    connection.rollback()
                    st.error(f"Unexpected error executing query: {e}")
                    raise

    def execute_batch_insert(self, query: str, values: List[tuple]):
        with self.pool.get_connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.executemany(query, values)
                    connection.commit()
                except mysql.connector.Error as e:
                    st.error(f"Error executing batch insert: {e}")

    def fetch_one(self, query: str, values: tuple = None):
        with self.pool.get_connection() as connection:
            with connection.cursor() as cursor:
                try:
                    if values:
                        cursor.execute(query, values)
                    else:
                        cursor.execute(query)
                    return cursor.fetchone()
                except mysql.connector.Error as e:
                    st.error(f"Error fetching data: {e}")

    def fetch_all(self, query: str, values: tuple = None):
        with self.pool.get_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                try:
                    if values:
                        cursor.execute(query, values)
                    else:
                        cursor.execute(query)
                    return cursor.fetchall()
                except mysql.connector.Error as e:
                    st.error(f"Error fetching data: {e}")
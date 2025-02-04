import json
import random
import sqlalchemy
import streamlit as st

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials



class UsersTable:
    def __init__(self):
        credentials = Credentials.from_service_account_file("config/cloud_sql_editor_service_account_key.json")

        self.connector = Connector(credentials=credentials)
        self.db_password = st.secrets["CLOUD_SQL_PASSWORD"]


    def _get_connection(self):
        conn = self.connector.connect(
            "project-mlb-tool-tips:us-central1:admin",
            "pymysql",
            user="root",
            password=self.db_password,
            db="mlb_db"
        )
        return conn


    def create_table(self):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            try:
                query = sqlalchemy.text(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id VARCHAR(255) PRIMARY KEY,
                        favorite_team_id VARCHAR(255),
                        followed_player_ids VARCHAR(255),
                        followed_team_ids VARCHAR(255),
                    );
                    """
                )

                db_conn.execute(query)
                return True
            
            except Exception as error:
                return False

    def add_user(self, user_id, favorite_team_id="", followed_player_ids=[], followed_team_ids=[]):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            try:
                query = sqlalchemy.text(
                    """
                    INSERT INTO users (
                    user_id, favorite_team_id, followed_player_ids, followed_team_ids
                    )
                    VALUES (
                    :user_id, :favorite_team_id, :followed_player_ids, :followed_team_ids
                    )
                    """
                )
                
                db_conn.execute(
                    query,
                    parameters={
                        "user_id": str(user_id), 
                        "favorite_team_id": str(favorite_team_id), 
                        "followed_player_ids": str(followed_player_ids), 
                        "followed_team_ids": str(followed_team_ids)
                    }
                )

                db_conn.commit()
                return True

            except Exception as error:
                db_conn.commit()
                return False


if __name__ == "__main__":
    users_table = UsersTable()
    ans = users_table.add_user("testuser", "123", "[123, 345, 456]", "[]")
    print(ans)
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Nanmai@2006",
        database="RFID_LIBRARY"
    )
import sqlite3
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME = "declutter_inventory.db"

def init_db():
    """
    Initializes the SQLite database and creates the items table if it doesn't exist.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                condition TEXT,
                decision TEXT,
                value_rp INTEGER,
                recommendations TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def save_item(name: str, category: str, condition: str, decision: str, price: float, recommendations: str) -> bool:
    """
    Saves a decluttered item and agent decisions to the inventory database.
    
    Args:
        name (str): Item name.
        category (str): Item category.
        condition (str): Apparent condition.
        decision (str): Final keep/sell/donate/recycle decision.
        price (float): Recommended price.
        recommendations (str): Actionable advice.
        
    Returns:
        bool: True if insertion succeeded, False otherwise.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO items (name, category, condition, decision, value_rp, recommendations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, category, condition, decision, int(price), recommendations, created_at))
        conn.commit()
        conn.close()
        logger.info(f"Item '{name}' saved successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to save item: {e}")
        return False

def get_inventory() -> list:
    """
    Fetches all decluttered items from the database.
    
    Returns:
        list: List of records in the database. Each record is a dictionary.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items ORDER BY id DESC")
        rows = cursor.fetchall()
        inventory = [dict(row) for row in rows]
        conn.close()
        return inventory
    except Exception as e:
        logger.error(f"Failed to fetch inventory: {e}")
        return []

def delete_inventory_item(item_id: int) -> bool:
    """
    Deletes an item from the inventory database.
    
    Args:
        item_id (int): Row ID of the item.
        
    Returns:
        bool: True if deletion succeeded, False otherwise.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        logger.info(f"Item with ID {item_id} deleted successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete item: {e}")
        return False

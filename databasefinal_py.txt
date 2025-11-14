import sqlite3
from datetime import datetime, timedelta

# Define the database file name
DB_NAME = 'inventory.db'
SQL_DUMP_FILE = 'inventory.sql' # New: Define the SQL file name

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    # Allows results to be returned as dictionaries (rows) instead of tuples
    conn.row_factory = sqlite3.Row
    return conn

def initialize_with_sql_dump(sql_filepath):
    """
    Reads a SQL file and executes all commands to initialize the database
    with structure and starting data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        with open(sql_filepath, 'r') as f:
            sql_script = f.read()
        
        # Execute the entire script at once (this handles CREATE, DROP, INSERT)
        cursor.executescript(sql_script)
        conn.commit()
        print(f"SUCCESS: Database initialized and populated from {sql_filepath}.")
        
    except FileNotFoundError:
        print(f"ERROR: SQL dump file '{sql_filepath}' not found. Database not populated.")
        print("Please save the provided SQL content into a file named 'inventory.sql'.")
    except sqlite3.Error as e:
        print(f"Database error during SQL dump execution: {e}")
    finally:
        conn.close()


# --- Core Functions (No changes needed, they use the new tables implicitly) ---

# NOTE: The setup_database function is now redundant for schema creation 
# because the SQL dump handles CREATE TABLE, but we keep the connection logic.
def setup_database():
    """Placeholder function to ensure connection and print message."""
    conn = get_db_connection()
    conn.close()
    print(f"Database setup verified. Using {DB_NAME}.")


def _get_or_create_product_id(product_name, category, conn):
    """Finds or creates a product and returns its ID."""
    cursor = conn.cursor()
    
    # 1. Try to find the existing product (ignoring deleted items)
    cursor.execute("SELECT id FROM products WHERE name = ? AND is_deleted = 0", (product_name,))
    result = cursor.fetchone()

    if result:
        # If found, ensure category is set (optional update)
        cursor.execute("UPDATE products SET category = ? WHERE id = ?", (category, result['id']))
        return result['id']
    else:
        # 2. Product not found, insert new record (and set category)
        cursor.execute("INSERT INTO products (name, category) VALUES (?, ?)", (product_name, category))
        return cursor.lastrowid

def add_stock(product_name, category, quantity_to_add, expiry_date_str):
    """Adds a NEW batch of stock with a specific quantity and expiry date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_date_str = datetime.now().strftime('%Y-%m-%d')
    
    try:
        product_id = _get_or_create_product_id(product_name, category, conn)

        # Check if product is already deleted (shouldn't happen with _get_or_create, but good practice)
        cursor.execute("SELECT is_deleted FROM products WHERE id = ?", (product_id,))
        if cursor.fetchone()['is_deleted'] == 1:
            return f"Error: Product '{product_name}' is in the Bin and cannot receive new stock."

        cursor.execute("""
            INSERT INTO batches 
            (product_id, quantity, entry_date, expiry_date) 
            VALUES (?, ?, ?, ?)
        """, (product_id, quantity_to_add, current_date_str, expiry_date_str))

        conn.commit()
        
        total_stock = check_stock(product_name)
        return f"Added new batch of {product_name} ({quantity_to_add} units). Total stock is now: {total_stock}"
    
    except sqlite3.Error as e:
        return f"Error adding stock: {e}"
    finally:
        conn.close()


def check_stock(product_name):
    """Calculates the SUM of active stock across all batches for a single product."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT SUM(T2.quantity) as total_quantity
            FROM products T1
            INNER JOIN batches T2 ON T1.id = T2.product_id
            WHERE T1.name = ? AND T1.is_deleted = 0
        """, (product_name,))
        
        result = cursor.fetchone()
        
        return result['total_quantity'] if result and result['total_quantity'] is not None else 0
    
    except sqlite3.Error as e:
        print(f"Error checking stock: {e}")
        return -1 
    finally:
        conn.close()
def get_low_stock_report():
    """
    Returns a list of products where the total active stock (sum of batches) 
    is at or below the reorder level.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                p.name,
                p.reorder_level,
                SUM(b.quantity) as total_quantity
            FROM products p
            INNER JOIN batches b ON p.id = b.product_id
            WHERE p.is_deleted = 0
            GROUP BY p.id, p.name, p.reorder_level
            HAVING SUM(b.quantity) <= p.reorder_level
            ORDER BY p.name
        """)
        
        return cursor.fetchall()
        
    except sqlite3.Error as e:
        print(f"Error generating low stock report: {e}")
        return []
    finally:
        conn.close()
        

def process_sale(product_name, quantity_sold):
    """
    Reduces stock quantity based on FIFO (First-In, First-Out) principle.
    It sells from the batch with the EARLIEST expiry date first.
    (Existing logic, omitted for brevity)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Check if the product exists and is active
        cursor.execute("SELECT id FROM products WHERE name = ? AND is_deleted = 0", (product_name,))
        product_result = cursor.fetchone()
        if not product_result:
            return f"Error: Product '{product_name}' not found or is inactive."

        product_id = product_result['id']
        current_stock = check_stock(product_name)
        
        if current_stock < quantity_sold:
            return f"Error: Cannot sell {quantity_sold} units. Only {current_stock} units of {product_name} available."

        remaining_to_sell = quantity_sold

        # 2. Get all batches for the product, ordered by earliest expiry date (FIFO)
        cursor.execute("""
            SELECT id, quantity 
            FROM batches 
            WHERE product_id = ? AND quantity > 0
            ORDER BY expiry_date ASC
        """, (product_id,))
        
        batches = cursor.fetchall()

        # 3. Process the sale against batches (FIFO loop)
        for batch in batches:
            if remaining_to_sell <= 0:
                break
            
            batch_id = batch['id']
            batch_qty = batch['quantity']
            
            if batch_qty >= remaining_to_sell:
                # This batch covers the remaining quantity needed
                new_qty = batch_qty - remaining_to_sell
                cursor.execute("UPDATE batches SET quantity = ? WHERE id = ?", (new_qty, batch_id))
                remaining_to_sell = 0 # Sale complete
            else:
                # The entire batch is sold out
                remaining_to_sell -= batch_qty
                cursor.execute("UPDATE batches SET quantity = 0 WHERE id = ?", (batch_id,))

        conn.commit()
        
        # 4. Return final stock count
        new_total_stock = check_stock(product_name)
        return f"Sale confirmed: {quantity_sold} units of {product_name} sold. Remaining stock: {new_total_stock}."

    except sqlite3.Error as e:
        return f"Database error during sale processing: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
    finally:
        conn.close()
        
# The remaining functions (set_reorder_level, get_low_stock_report, get_expiry_report, 
# soft_delete_product, get_deleted_products, restore_product) 
# are assumed to be included here, as they were in the previous version.


# --- Execution Block (Connects the SQL Dump) ---
if __name__ == '__main__':
    
    # 1. Create the inventory.sql file content
    sql_content = """
-- Enable foreign key support in SQLite
PRAGMA foreign_keys = ON;

--
-- Table structure for table `products`
--
DROP TABLE IF EXISTS `products`;

CREATE TABLE `products` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT NOT NULL,
  `category` TEXT,
  `reorder_level` INTEGER DEFAULT 10,
  `is_deleted` INTEGER DEFAULT 0
);

--
-- Dumping data for table `products`
--
INSERT INTO `products` (`id`, `name`, `category`, `reorder_level`, `is_deleted`) VALUES
(1, 'Milk Cartons', 'Dairy', 10, 0),
(2, 'Dozen Eggs', 'Dairy', 20, 0),
(3, 'Loaf of Bread', 'Bakery', 15, 0),
(4, 'Apples (Bag)', 'Produce', 10, 0),
(5, 'Cereal Box', 'Pantry', 25, 0),
(6, 'Chicken Breast (kg)', 'Meat', 10, 0),
(7, 'Orange Juice', 'Beverages', 15, 0);

--
-- Table structure for table `batches`
--
DROP TABLE IF EXISTS `batches`;

CREATE TABLE `batches` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `product_id` INTEGER NOT NULL,
  `quantity` INTEGER NOT NULL DEFAULT 0,
  `entry_date` DATE NOT NULL,
  `expiry_date` DATE,
  FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
);

--
-- Dumping data for table `batches`
--
-- Note: Dates are set around November 2025 to match your screenshots.
--
INSERT INTO `batches` (`id`, `product_id`, `quantity`, `entry_date`, `expiry_date`) VALUES
(1, 1, 0, '2025-11-14', '2025-11-24'), 
(2, 1, 0, '2025-11-14', '2025-11-16'), 
(3, 1, 50, '2025-11-14', '2025-12-14'), 
(4, 2, 100, '2025-11-10', '2025-12-01'), 
(5, 3, 75, '2025-11-13', '2025-11-20'), 
(6, 4, 120, '2025-11-12', '2025-11-26'), 
(7, 5, 80, '2025-10-30', '2026-05-01'), 
(8, 6, 30, '2025-11-14', '2025-11-21'), 
(9, 6, 40, '2025-11-15', '2025-11-22'), 
(10, 7, 60, '2025-11-05', '2026-02-05'),
(11, 2, 50, '2025-11-01', '2025-11-10');
"""
    
    # 2. Write the content to inventory.sql file (optional, but ensures it exists)
    try:
        with open(SQL_DUMP_FILE, 'w') as f:
            f.write(sql_content)
    except Exception as e:
        print(f"Failed to write internal SQL dump file: {e}")

    # 3. Initialize the database using the SQL dump
    initialize_with_sql_dump(SQL_DUMP_FILE)
    
    # 4. Run setup (to show completion message)
    setup_database()
    
    # 5. Example usage (to verify data is loaded)
    print(f"\n--- Verification of Loaded Data ---")
    print(f"Total Milk Cartons Stock: {check_stock('Milk Cartons')} (Expected 50)") 
    print(f"Low Stock Report (Grapes - should be empty): {get_low_stock_report()}")
    print(f"Sale of 5 units of Milk: {process_sale('Milk Cartons', 5)}") 
    print(f"Remaining Milk Stock: {check_stock('Milk Cartons')} (Expected 45)")
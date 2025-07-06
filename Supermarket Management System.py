import mysql.connector as mc
from datetime import datetime
from decimal import Decimal
import time as t

def connect_db():
    return mc.connect(
        host='localhost',
        user='root',
        password=password,
        database='Supermarket'
    )

def setup_database():
    global password
    password = input('\nEnter Password of the Server: ')
    db = mc.connect(
        host='localhost',
        user='root',
        password=password,
    )
    cursor = db.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS Supermarket")
    cursor.execute("USE Supermarket")

    def check_and_create_table(cursor, table_name, desired_structure):
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        result = cursor.fetchone()

        if result:
            cursor.execute(f"DESC {table_name}")
            current_table_structure = {}
            for row in cursor.fetchall():
                current_table_structure[row[0]] = row[1]

            for column_name, column_type in desired_structure.items():
                if column_name not in current_table_structure:
                    cursor.execute(f"ALTER TABLE {table_name} ADD {column_name} {column_type}")
                elif current_table_structure[column_name] != column_type:
                    cursor.execute(f"SHOW KEYS FROM {table_name} WHERE Column_name = '{column_name}' AND Key_name = 'PRIMARY'")
                    if not cursor.fetchone():
                        cursor.execute(f"ALTER TABLE {table_name} MODIFY {column_name} {column_type}")
        else:
            columns_list = []
            for column_name, column_type in desired_structure.items():
                columns_list.append(f"{column_name} {column_type}")
            columns = ', '.join(columns_list)

            cursor.execute(f"CREATE TABLE {table_name} ({columns})")

    desired_products_structure = {
        'ProductID': 'INT AUTO_INCREMENT PRIMARY KEY',
        'ProductName': 'VARCHAR(255) NOT NULL',
        'Stock': 'INT NOT NULL',
        'Price': 'DECIMAL(10, 2) NOT NULL',
    }

    desired_bills_structure = {
        'BillID': 'INT AUTO_INCREMENT PRIMARY KEY',
        'Date': 'DATETIME NOT NULL',
        'TotalAmount': 'DECIMAL(10, 2) NOT NULL',
        'CustomerContact': 'VARCHAR(50)',
        'PaymentMethod': 'VARCHAR(50)',
        'CustomerName': 'VARCHAR(255)'      
    }

    desired_bill_details_structure = {
        'BillDetailID': 'INT AUTO_INCREMENT PRIMARY KEY',
        'BillID': 'INT',
        'ProductID': 'INT',
        'Quantity': 'INT NOT NULL',
        'Price': 'DECIMAL(10, 2) NOT NULL',
    }

    check_and_create_table(cursor, 'Products', desired_products_structure)
    check_and_create_table(cursor, 'Bills', desired_bills_structure)
    check_and_create_table(cursor, 'BillDetails', desired_bill_details_structure)

    cursor.execute(""" 
        SELECT CONSTRAINT_NAME 
        FROM information_schema.KEY_COLUMN_USAGE 
        WHERE TABLE_NAME = 'BillDetails' AND TABLE_SCHEMA = 'Supermarket' 
        AND (CONSTRAINT_NAME = 'foreign_key_bill' OR CONSTRAINT_NAME = 'foreign_key_product')
    """)
    existing_foreign_keys = set()
    for row in cursor.fetchall():
        existing_foreign_keys.add(row[0])

    if 'foreign_key_bill' not in existing_foreign_keys:
        cursor.execute("ALTER TABLE BillDetails ADD CONSTRAINT foreign_key_bill FOREIGN KEY (BillID) REFERENCES Bills(BillID)")

    if 'foreign_key_product' not in existing_foreign_keys:
        cursor.execute("ALTER TABLE BillDetails ADD CONSTRAINT foreign_key_product FOREIGN KEY (ProductID) REFERENCES Products(ProductID)")

    db.commit()
    cursor.close()
    db.close()

def admin_mode():
    while True:
        print("\n\n========== [Admin Mode] ==========")
        print("1. Add New Product")
        print("2. Remove Product")
        print("3. View Inventory")
        print("4. Update Inventory")
        print("5. Restock")
        print("6. Exit")
        
        option = input("Select an option: ")
        
        if option == '1':
            add_new_product()
        elif option == '2':
            remove_product()
        elif option == '3':
            view_inventory()
        elif option == '4':
            update_inventory()
        elif option == '5':
            restock()
        elif option == '6':
            break
            
        else:
            print("Invalid option. Please try again.")

def add_new_product(name=None, price=None, stock=None):
    if name is None or price is None or stock is None:
        name = input("Enter product name: ")
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Products WHERE ProductName = %s", (name,))
        if cursor.fetchone():
            print("Product already exists in the inventory.")
            cursor.close()
            db.close()
            return

        while True:
            try:
                price = float(input("Enter product price: "))
                stock = int(input("Enter product stock: "))
                if price < 0 or stock < 0:
                    print("Price and stock cannot be negative. Please enter valid values.")
                    continue
                break
            except ValueError:
                print("Invalid price or stock. Please enter valid numbers.")

    if price < 0 or stock < 0:
        print("Price and stock cannot be negative. Please enter valid values.")
        return

    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Products WHERE ProductName = %s", (name,))
    existing_product = cursor.fetchone()

    if existing_product:
        cursor.close()
        db.close()
        return

    cursor.execute("SELECT MAX(ProductID) FROM Products")
    max_id = cursor.fetchone()[0]
    new_id = 1 if max_id is None else max_id + 1
    
    cursor.execute("INSERT INTO Products (ProductID, ProductName, Price, Stock) VALUES (%s, %s, %s, %s)", 
                   (new_id, name, price, stock))
    db.commit()
    cursor.close()
    db.close()

def remove_product():
    product_input = input("Enter Product ID or Product Name to remove: ")

    db = connect_db()
    cursor = db.cursor()

    if product_input.isdigit():
        cursor.execute("SELECT * FROM Products WHERE ProductID = %s", (int(product_input),))
    else:
        cursor.execute("SELECT * FROM Products WHERE ProductName = %s", (product_input,))

    product = cursor.fetchone()
    
    if not product:
        print("Product not found.")
        cursor.close()
        db.close()
        return

    product_id, product_name, stock, price = product

    cursor.execute("SELECT * FROM BillDetails WHERE ProductID = %s", (product_id,))
    if cursor.fetchone():
        print(f"Product '{product_name}' is already associated with an existing bill.")
        
        choice = input("Would you like to set the stock to 0 instead of deleting it? (Y/N): ").strip().lower()
        if choice == 'y':
            cursor.execute("UPDATE Products SET Stock = 0 WHERE ProductID = %s", (product_id,))
            db.commit()
            print(f"Stock for product '{product_name}' has been set to 0.")
        else:
            print(f"Product '{product_name}' was not deleted.")
    else:
        cursor.execute("DELETE FROM Products WHERE ProductID = %s", (product_id,))
        db.commit()
        print(f"Product '{product_name}' has been successfully removed from the inventory.")

    cursor.close()
    db.close()

def view_inventory():
    db = connect_db()
    cursor = db.cursor()
    
    product_input = input("Enter Product ID or Product Name to search (Press Enter to view all products): ")

    if product_input == "":  
        cursor.execute("SELECT * FROM Products")
    elif product_input.isdigit():
        cursor.execute("SELECT * FROM Products WHERE ProductID = %s", (int(product_input),))
    else:
        cursor.execute("SELECT * FROM Products WHERE ProductName LIKE %s", ('%' + product_input + '%',))

    products = cursor.fetchall()

    if not products:
        print("No products found.")
    else:
        print("\n=====================  [Inventory]  =========================")
        print("Product ID     Product Name          Price        Stock")
        print("=============================================================")

        for product in products:
            print(f"{product[0]:<15} {product[1]:<20} {product[3]:<12} {product[2]}")

        print("=============================================================")

    cursor.close()
    db.close()

def update_inventory():
    db = connect_db()
    cursor = db.cursor()
    
    product_input = input("Enter Product ID or Product Name to update: ")

    if product_input.isdigit():
        cursor.execute("SELECT * FROM Products WHERE ProductID = %s", (int(product_input),))
    else:
        cursor.execute("SELECT * FROM Products WHERE ProductName = %s", (product_input,))

    product = cursor.fetchone()

    if not product:
        print("Product not found. Please enter a valid Product ID or Name.")
        cursor.close()
        db.close()
        return

    product_id, product_name, stock, price = product

    print(f"\nCurrent details for {product_name}:")
    print(f"Stock: {stock}")
    print(f"Price: Rs.{price:.2f}")

    update_stock = input("Would you like to update the stock (y/n)? ").lower()
    if update_stock == 'y' or update_stock == 'yes':
        while True:
            try:
                stock_change = int(input(f"Enter the stock change for {product_name} (positive for addition, negative for removal): "))
                break
            except ValueError:
                print("Invalid input. Please enter a valid number.")

        new_stock = stock + stock_change

        if new_stock < 0:
            print("Cannot update stock. Stock cannot be negative.")
        else:
            cursor.execute("UPDATE Products SET Stock = %s WHERE ProductID = %s", (new_stock, product_id))
            db.commit()
            print(f"Stock for {product_name} has been updated to {new_stock}.")

    update_price = input("Would you like to update the price (y/n)? ").lower()
    if update_price == 'y' or update_price == 'yes':
        while True:
            try:
                new_price = float(input(f"Enter the new price for {product_name}: Rs."))
                if new_price < 0:
                    print("Price cannot be negative. Please enter a valid price.")
                else:
                    break
            except ValueError:
                print("Invalid input. Please enter a valid price.")

        cursor.execute("UPDATE Products SET Price = %s WHERE ProductID = %s", (new_price, product_id))
        db.commit()
        print(f"Price for {product_name} has been updated to Rs.{new_price:.2f}.")

    cursor.close()
    db.close()

def generate_receipt(bill_id, bill_date, customer_name, customer_contact, payment_method, products, subtotal, gst, total_amount):
    print('Generating Receipt', end='', flush=True)
    for _ in range(3):
        t.sleep(0.5)
        print('.', end='', flush=True)
    t.sleep(1)
    print()

    print("\n" + "="*40)
    print(" " * 15 + " Receipt ")
    print("="*40)

    print(f"Bill ID: {bill_id:<20}")
    print(f"Date: {bill_date.strftime('%d %B %Y')} || Time: {bill_date.strftime('%I:%M %p'):<20}")
    print(f"Customer Name: {customer_name:<20}")
    print(f"Customer Contact: {customer_contact:<20}")
    print(f"Payment Method: {payment_method:<20}")
    
    print("="*40)
    print(f"{'Product Name':<20} {'Quantity':<12} {'Price':<12}")
    print("="*40)

    for _, product_name, quantity, price in products:
        print(f"{product_name:<20} {quantity:<12} {Decimal(price):<12.2f}")

    print("="*40)
    print(f"Subtotal: {subtotal:<12.2f}")
    print(f"GST (5%): {gst:<12.2f}")
    print(f"Total Amount: {total_amount:<12.2f}")

    print("="*40)

def create_new_bill():
    customer_name = input("Enter the name of the customer: ")
    customer_contact = input("Enter the customer's contact number/email: ")
    payment_method = input("Enter the payment method (e.g., Cash, Credit, etc.): ")
    bill_date = datetime.now()

    products = []
    db = connect_db()
    cursor = db.cursor()

    while True:
        product_input = input("Enter Product ID or Product Name (or -1 to finish): ")
        if product_input == "-1":
            break

        try:
            if product_input.isdigit():
                cursor.execute("SELECT * FROM Products WHERE ProductID = %s", (int(product_input),))
            else:
                cursor.execute("SELECT * FROM Products WHERE ProductName = %s", (product_input,))

            product = cursor.fetchone()
            if product:
                product_id, product_name, stock, price = product
                quantity_input = input(f"Enter quantity for {product_name}: ")

                try:
                    quantity = int(quantity_input)
                except ValueError:
                    print("Invalid quantity. Please enter a valid integer.")
                    continue

                if quantity <= stock:
                    product_exists = False
                    for i, p in enumerate(products):
                        if p[0] == product_id:
                            product_exists = True
                            products[i] = (product_id, product_name, p[2] + quantity, price)
                            break

                    if not product_exists:
                        products.append((product_id, product_name, quantity, price))
                else:
                    print("Insufficient stock. Please try again.")
            else:
                print("Product not found. Please enter a valid Product ID or Name.")
        except Exception as e:
            print(f"An error occurred: {e}")

    if not products:
        print("No products were added. Cancelling the bill creation.")
        cursor.close()
        db.close()
        return

    subtotal = sum(quantity * Decimal(price) for _, _, quantity, price in products)
    gst = subtotal * Decimal('0.05')
    total_amount = subtotal + gst

    cursor.execute(
        "INSERT INTO Bills (Date, TotalAmount, CustomerContact, PaymentMethod, CustomerName) VALUES (%s, %s, %s, %s, %s)", 
        (bill_date, total_amount, customer_contact, payment_method, customer_name)
    )
    db.commit()

    cursor.execute("SELECT LAST_INSERT_ID()")
    bill_id = cursor.fetchone()[0]

    for product_id, _, quantity, price in products:
        cursor.execute("UPDATE Products SET Stock = Stock - %s WHERE ProductID = %s", (quantity, product_id))

    for product_id, product_name, quantity, price in products:
        cursor.execute("INSERT INTO BillDetails (BillID, ProductID, Quantity, Price) VALUES (%s, %s, %s, %s)",
                       (bill_id, product_id, quantity, price))

    db.commit()
    cursor.close()
    db.close()

    generate_receipt(bill_id, bill_date, customer_name, customer_contact, payment_method, products, subtotal, gst, total_amount)

    print(f" Thanks For Shopping At APS Supermarket!")
    print("="*40)

def check_previous_bills():
    db = connect_db()
    cursor = db.cursor()

    bill_id_input = input("Enter Bill ID to view a specific bill or press Enter to view all bills: ")

    if bill_id_input.strip():
        try:
            cursor.execute("""
                SELECT b.BillID, b.Date, b.CustomerName, b.CustomerContact, b.PaymentMethod, b.TotalAmount
                FROM Bills b WHERE b.BillID = %s
            """, (bill_id_input,))
            bill = cursor.fetchone()

            if bill:
                bill_id, bill_date, customer_name, customer_contact, payment_method, total_amount = bill
                print("\n" + "="*40)
                print(" " * 15 + " Receipt ")
                print("="*40)

                print(f"Bill ID: {bill_id:<20}")
                print(f"Date: {bill_date.strftime('%d %B %Y')} || Time: {bill_date.strftime('%I:%M %p'):<20}")
                print(f"Customer Name: {customer_name:<20}")
                print(f"Customer Contact: {customer_contact:<20}")
                print(f"Payment Method: {payment_method:<20}")

                cursor.execute("""
                    SELECT p.ProductName, bd.Quantity, bd.Price
                    FROM BillDetails bd
                    JOIN Products p ON bd.ProductID = p.ProductID
                    WHERE bd.BillID = %s
                """, (bill_id,))
                products = cursor.fetchall()

                print("="*40)
                print(f"{'Product Name':<20} {'Quantity':<12} {'Price':<12}")
                print("="*40)

                for product_name, quantity, price in products:
                    print(f"{product_name:<20} {quantity:<12} {Decimal(price):<12.2f}")

                print("="*40)
                print(f"Total Amount: {total_amount:<12.2f}")
                print("="*40)

            else:
                print(f"Bill ID {bill_id_input} not found.")

        except mc.connector.Error as err:
            print(f"Error: {err}")

    else:
        try:
            cursor.execute("""
                SELECT BillID, Date, TotalAmount, CustomerName FROM Bills
            """)
            bills = cursor.fetchall()

            print("\n======================== [Previous Bills] ============================")
            print(f"{'Bill ID':<10} {'Date':<25} {'Total Amount':<15} {'Customer Name':<20}")
            print("="*70)

            for bill in bills:
                bill_id, bill_date, total_amount, customer_name = bill
                print(f"{bill_id:<10} {bill_date.strftime('%d %B %Y || %I:%M %p'):<25} {Decimal(total_amount):<15.2f} {customer_name:<20}")

            print("="*70)

        except mc.connector.Error as err:
            print(f"Error: {err}")

def issue_return():
    bill_id = input("Enter the Bill ID for the return: ")

    db = connect_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM Bills WHERE BillID = %s", (bill_id,))
    bill = cursor.fetchone()

    if not bill:
        print("Bill not found. Please enter a valid Bill ID.")
        cursor.close()
        db.close()
        return

    cursor.execute("""
        SELECT Bills.BillID, Bills.Date, Bills.CustomerName, Bills.CustomerContact, Bills.PaymentMethod, Bills.TotalAmount 
        FROM Bills 
        WHERE Bills.BillID = %s
    """, (bill_id,))
    bill_details = cursor.fetchone()

    bill_id, bill_date, customer_name, customer_contact, payment_method, total_amount = bill_details
    print("\n" + "=" * 40)
    print(" " * 12 + " Receipt ")
    print("=" * 40)

    print(f"Bill ID: {bill_id:<20}")
    print(f"Date: {bill_date.strftime('%d %B %Y')} || Time: {bill_date.strftime('%I:%M %p'):<20}")
    print(f"Customer Name: {customer_name:<20}")
    print(f"Customer Contact: {customer_contact:<20}")
    print(f"Payment Method: {payment_method:<20}")

    cursor.execute("""
        SELECT Products.ProductName, BillDetails.Quantity, BillDetails.Price 
        FROM BillDetails 
        JOIN Products ON BillDetails.ProductID = Products.ProductID 
        WHERE BillDetails.BillID = %s
    """, (bill_id,))
    products = cursor.fetchall()

    print("=" * 40)
    print(f"{'Product Name':<20} {'Quantity':<12} {'Price':<12}")
    print("=" * 40)

    products_in_bill = []
    for product_name, quantity, price in products:
        print(f"{product_name:<20} {quantity:<12} {Decimal(price):<12.2f}")
        products_in_bill.append((product_name, quantity, price))

    print("=" * 40)
    print(f"Total Amount: {total_amount:<12.2f}")
    print("=" * 40)

    product_to_return = input("\nEnter the Product Name to return: ")

    valid_product = None
    for product_name, quantity, price in products_in_bill:
        if product_name.lower() == product_to_return.lower():
            valid_product = (product_name, quantity, price)
            break

    if not valid_product:
        print("Product not found in this bill. Please try again.")
        cursor.close()
        db.close()
        return

    product_name, original_quantity, price = valid_product
    return_quantity = int(input(f"Enter the quantity to return (max {original_quantity}): "))

    if return_quantity <= original_quantity:
        cursor.execute("SELECT ProductID FROM Products WHERE ProductName = %s", (product_name,))
        product_id = cursor.fetchone()[0]

        cursor.execute("UPDATE Products SET Stock = Stock + %s WHERE ProductID = %s", (return_quantity, product_id))

        new_quantity = original_quantity - return_quantity

        if new_quantity == 0:
            cursor.execute("DELETE FROM BillDetails WHERE BillID = %s AND ProductID = %s", (bill_id, product_id))
        else:
            cursor.execute("UPDATE BillDetails SET Quantity = %s WHERE BillID = %s AND ProductID = %s", (new_quantity, bill_id, product_id))

        print(f"{return_quantity} of '{product_name}' returned successfully.")
        
        gst_rate = Decimal('5') / Decimal('100')
        gst_refund = (return_quantity * price) * gst_rate
        total_refund = (return_quantity * price) + gst_refund
        new_total_amount = total_amount - total_refund
        cursor.execute("UPDATE Bills SET TotalAmount = %s WHERE BillID = %s", (new_total_amount, bill_id))
        print(f"Updated Total Amount (including GST refund): {new_total_amount:.2f}")
    else:
        print("Return quantity exceeds purchased quantity. Please try again.")

    db.commit()
    cursor.close()
    db.close()  

def restock():
    add_new_product(name="Shampoo", price=180, stock=50)
    add_new_product(name="Toothpaste", price=90, stock=70)
    add_new_product(name="Soap", price=40, stock=100)
    add_new_product(name="Dishwashing Liquid", price=100, stock=50)
    add_new_product(name="Washing Powder", price=150, stock=80)
    add_new_product(name="Chips", price=20, stock=200)
    add_new_product(name="Biscuits", price=30, stock=180)
    add_new_product(name="Soft Drink", price=80, stock=50)
    add_new_product(name="Tea", price=120, stock=60)
    add_new_product(name="Coffee", price=150, stock=40)
    add_new_product(name="Rice", price=250, stock=50)
    add_new_product(name="Wheat Flour", price=200, stock=70)
    add_new_product(name="Sugar", price=45, stock=100)
    add_new_product(name="Tur Dal", price=120, stock=50)
    add_new_product(name="Salt", price=20, stock=200)
    add_new_product(name="Potato", price=30, stock=150)
    add_new_product(name="Tomato", price=40, stock=100)
    add_new_product(name="Onion", price=50, stock=120)
    add_new_product(name="Banana", price=60, stock=80)
    add_new_product(name="Apple", price=150, stock=50)
    add_new_product(name="Milk", price=60, stock=100)
    add_new_product(name="Butter", price=250, stock=40)
    add_new_product(name="Eggs", price=70, stock=60)
    add_new_product(name="Bread", price=40, stock=80)
    add_new_product(name="Paneer", price=80, stock=30)

def main():
    setup_database()
    restock()

    while True:
        print("\n========== [Main Menu] ==========")
        print("1. Create New Bill")
        print("2. Check Previous Bills")
        print("3. Issue Return")
        print("4. Exit")
        
        option = input("Select an option: ")

        if option == 'admin':
            admin_pass = input('Enter the password to enter ADMIN_MODE: ')
            print('Checking Password.', end='', flush=True)
            for _ in range(3):
                    t.sleep(0.3)
                    print('.', end='', flush=True)
            t.sleep(1)
            print()           
            if admin_pass == 'secret':
                print('Password correct')
                print('Entering ADMIN_MODE.', end='', flush=True)
                for _ in range(3):
                    t.sleep(0.3)
                    print('.', end='', flush=True)
                t.sleep(.5)
                admin_mode()
                print()
                        
            else: 
                print('Wrong Password.. Try again...')

        elif option == '1':
            create_new_bill()
        elif option == '2':
            check_previous_bills()
        elif option == '3':
            issue_return() 
        elif option == '4':
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
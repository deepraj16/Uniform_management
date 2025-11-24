import pymysql
import pymysql

def create_students_table():
    try:
        # --- Connect to MySQL ---
        connection = pymysql.connect(
            host="localhost",
            user="root",
            password="1234",
            database="attendance"
        )

        cursor = connection.cursor()

        # --- Create Table Query ---
        create_table_query = """
        CREATE TABLE IF NOT EXISTS students (
            id INT PRIMARY KEY,
            student_name VARCHAR(100),
            username VARCHAR(100),
            password VARCHAR(100)
        );
        """

        cursor.execute(create_table_query)
        connection.commit()

        print("Table 'students' created successfully!")

    except Exception as e:
        print("Error creating table:", e)

    finally:
        cursor.close()
        connection.close()




def insert_student(id, student_name, username, password):
    try:
        # --- Connect to MySQL ---
        connection = pymysql.connect(
            host="localhost",
            user="root",
            password="1234",
            database="attendance"
        )

        cursor = connection.cursor()

        # --- Insert Query ---
        query = """
            INSERT INTO students (id, student_name, username, password)
            VALUES (%s, %s, %s, %s)
        """

        values = (id, student_name, username, password)

        cursor.execute(query, values)
        connection.commit()

        print("Student inserted successfully!")

    except Exception as e:
        print("Error inserting student:", e)

    finally:
        cursor.close()
        connection.close()

def view_students():
    try:
        # Connect to MySQL
        connection = pymysql.connect(
            host="localhost",
            user="root",
            password="1234",
            database="attendance"
        )

        cursor = connection.cursor()

        # Fetch all data
        cursor.execute("SELECT * FROM students;")
        rows = cursor.fetchall()

        print("\nStudents Table Data:")
        for row in rows:
            print(row)

    except Exception as e:
        print("Error:", e)

    finally:
        cursor.close()
        connection.close()


# Run function
view_students()

# ---- Example Usage ----

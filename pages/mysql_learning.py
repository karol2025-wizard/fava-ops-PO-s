"""
MySQL Learning Lab - Student Management System

This page helps you learn SQL by interacting with a MySQL database.
We'll work with a Student Management System that demonstrates:
- Multiple SQL data types (INT, VARCHAR, DATE, DECIMAL, BOOLEAN, TIMESTAMP)
- CRUD operations (Create, Read, Update, Delete)
- Database connections and queries
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import mysql.connector
from mysql.connector import Error
from config import secrets

# Page configuration
st.set_page_config(
    page_title="MySQL Learning Lab",
    page_icon="🎓",
    layout="wide",
    menu_items={'About': "# MySQL Learning Lab - Learn SQL by doing!"}
)

# Store SQL queries for display
if 'sql_queries' not in st.session_state:
    st.session_state.sql_queries = []


def get_db_connection():
    """Create and return a MySQL database connection. Creates database if it doesn't exist."""
    host = secrets.get('mysql_host', 'localhost')
    port = secrets.get('mysql_port', 3306)
    user = secrets.get('mysql_user', 'root')
    password = secrets.get('mysql_password', '')
    database = secrets.get('mysql_database', 'fava_ops')
    
    try:
        # First, try to connect to the database
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        return connection
    except Error as e:
        # If database doesn't exist (error 1049), create it
        if e.errno == 1049:  # Unknown database
            try:
                # Connect without specifying a database
                connection = mysql.connector.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password
                )
                cursor = connection.cursor()
                
                # Create the database
                create_db_query = f"CREATE DATABASE IF NOT EXISTS {database}"
                cursor.execute(create_db_query)
                connection.commit()
                cursor.close()
                connection.close()
                
                # Store the query for display
                st.session_state.sql_queries.append({
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'query': create_db_query
                })
                
                # Now connect to the newly created database
                connection = mysql.connector.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                st.success(f"✅ Database '{database}' created successfully!")
                return connection
            except Error as create_error:
                st.error(f"❌ **Error creating database:** {str(create_error)}")
                return None
        else:
            # Other connection errors
            st.error(f"❌ **Database connection error:** {str(e)}")
            st.info("""
            **Please configure your MySQL connection in `.streamlit/secrets.toml`:**
            ```toml
            mysql_host = "localhost"
            mysql_port = 3306
            mysql_user = "root"
            mysql_password = "your_password"
            mysql_database = "fava_ops"
            ```
            """)
            return None


def execute_query(connection, query: str, params: tuple = None, fetch: bool = True):
    """
    Execute a SQL query and return results
    
    Args:
        connection: MySQL connection object
        query: SQL query string
        params: Query parameters tuple (for parameterized queries)
        fetch: Whether to fetch results (True for SELECT, False for INSERT/UPDATE/DELETE)
    
    Returns:
        Query results if fetch=True, else number of affected rows
    """
    if connection is None:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        # Store the query for display
        formatted_query = query
        if params:
            # Simple parameter substitution for display (not for execution - we use parameterized queries)
            for param in params:
                if isinstance(param, str):
                    formatted_query = formatted_query.replace('%s', f"'{param}'", 1)
                else:
                    formatted_query = formatted_query.replace('%s', str(param), 1)
        
        st.session_state.sql_queries.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'query': formatted_query
        })
        
        if fetch:
            results = cursor.fetchall()
            connection.commit()
            cursor.close()
            return results
        else:
            connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
            
    except Error as e:
        st.error(f"❌ **SQL Error:** {str(e)}")
        connection.rollback()
        return None


def create_students_table(connection):
    """Create the students table if it doesn't exist"""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS students (
        student_id INT AUTO_INCREMENT PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        email VARCHAR(100) UNIQUE,
        date_of_birth DATE,
        enrollment_date DATE DEFAULT (CURRENT_DATE),
        gpa DECIMAL(3, 2) DEFAULT 0.00,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    execute_query(connection, create_table_query, fetch=False)
    return True


def create_classes_table(connection):
    """Create the classes table if it doesn't exist"""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS classes (
        class_id INT AUTO_INCREMENT PRIMARY KEY,
        class_name VARCHAR(100) NOT NULL,
        class_code VARCHAR(20) UNIQUE,
        instructor VARCHAR(100),
        credits INT DEFAULT 3,
        max_students INT DEFAULT 30,
        semester VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    execute_query(connection, create_table_query, fetch=False)
    return True


def create_student_classes_table(connection):
    """Create the student_classes enrollment table with foreign keys"""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS student_classes (
        enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        class_id INT NOT NULL,
        enrollment_date DATE DEFAULT (CURRENT_DATE),
        grade DECIMAL(4, 2),
        status VARCHAR(20) DEFAULT 'Enrolled',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE,
        UNIQUE KEY unique_enrollment (student_id, class_id)
    )
    """
    execute_query(connection, create_table_query, fetch=False)
    return True


def initialize_tables(connection):
    """Initialize all tables in the correct order (respecting foreign key dependencies)"""
    create_students_table(connection)
    create_classes_table(connection)
    create_student_classes_table(connection)


def main():
    st.title("🎓 MySQL Learning Lab - Student Management System")
    st.markdown("""
    Welcome to the MySQL Learning Lab! This page helps you learn SQL by working with a **Student Management System**.
    
    **What you'll learn:**
    - How to connect to a MySQL database
    - Different SQL data types (INT, VARCHAR, DATE, DECIMAL, BOOLEAN, TIMESTAMP)
    - CRUD operations (Create, Read, Update, Delete)
    - **Cross-table relationships (Foreign Keys, JOINs)**
    - **Many-to-many relationships**
    - Writing SQL queries
    
    Every action you take will show you the exact SQL query being executed!
    """)
    
    # Check configuration
    required_keys = ['mysql_host', 'mysql_user', 'mysql_password', 'mysql_database']
    missing_keys = [key for key in required_keys if key not in secrets]
    
    if missing_keys:
        st.error(f"⚠️ **Configuration required**: Missing keys: {', '.join(missing_keys)}")
        st.info("""
        **Please configure your MySQL connection in `.streamlit/secrets.toml`:**
        ```toml
        mysql_host = "localhost"
        mysql_port = 3306
        mysql_user = "root"
        mysql_password = "your_password"
        mysql_database = "fava_ops"
        ```
        """)
        with st.expander("🔍 View available keys in secrets"):
            available = list(secrets.keys())
            if available:
                st.write("**Available keys:**")
                for key in available:
                    st.write(f"- `{key}`")
            else:
                st.write("No keys found in secrets.")
        return
    
    # Connect to database
    connection = get_db_connection()
    if connection is None:
        return
    
    # Initialize tables
    with st.spinner("Initializing database..."):
        initialize_tables(connection)
        st.success("✅ Database connected and tables ready!")
    
    # Sidebar for SQL Query History
    with st.sidebar:
        st.header("📜 SQL Query History")
        st.markdown("Every SQL query executed is logged here:")
        st.markdown("---")
        
        if st.session_state.sql_queries:
            for idx, query_info in enumerate(reversed(st.session_state.sql_queries[-10:]), 1):  # Show last 10
                with st.expander(f"Query #{len(st.session_state.sql_queries) - idx + 1} - {query_info['timestamp']}"):
                    st.code(query_info['query'], language='sql')
        else:
            st.info("No queries executed yet. Start using the app to see SQL queries!")
        
        if st.button("🗑️ Clear Query History"):
            st.session_state.sql_queries = []
            st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 View Students", 
        "➕ Add Student", 
        "✏️ Update Student", 
        "🗑️ Delete Student",
        "📚 Classes",
        "➕ Add Class",
        "🔗 Enrollments",
        "➕ Enroll Student",
        "📖 Table Schema"
    ])
    
    # TAB 1: View Students
    with tab1:
        st.header("📊 View All Students")
        st.markdown("This section demonstrates the **SELECT** query.")
        
        if st.button("🔄 Refresh Student List"):
            st.rerun()
        
        query = "SELECT * FROM students ORDER BY student_id ASC"
        students = execute_query(connection, query, fetch=True)
        
        if students:
            df = pd.DataFrame(students)
            st.dataframe(df, use_container_width=True)
            st.success(f"✅ Found {len(students)} student(s)")
            
            # Show the SQL query
            st.markdown("**SQL Query Executed:**")
            st.code(query, language='sql')
        else:
            st.info("📝 No students found. Add a student using the 'Add Student' tab!")
    
    # TAB 2: Add Student
    with tab2:
        st.header("➕ Add New Student")
        st.markdown("This section demonstrates the **INSERT** query.")
        
        with st.form("add_student_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name *", placeholder="John")
                last_name = st.text_input("Last Name *", placeholder="Doe")
                email = st.text_input("Email", placeholder="john.doe@example.com")
                date_of_birth = st.date_input("Date of Birth", value=None)
            
            with col2:
                enrollment_date = st.date_input("Enrollment Date", value=date.today())
                gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, value=0.0, step=0.01, format="%.2f")
                is_active = st.checkbox("Active Student", value=True)
            
            submitted = st.form_submit_button("➕ Add Student", use_container_width=True)
            
            if submitted:
                if not first_name or not last_name:
                    st.error("❌ First Name and Last Name are required!")
                else:
                    insert_query = """
                    INSERT INTO students 
                    (first_name, last_name, email, date_of_birth, enrollment_date, gpa, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (
                        first_name,
                        last_name,
                        email if email else None,
                        date_of_birth if date_of_birth else None,
                        enrollment_date,
                        gpa,
                        is_active
                    )
                    
                    result = execute_query(connection, insert_query, params=params, fetch=False)
                    
                    if result:
                        st.success(f"✅ Student '{first_name} {last_name}' added successfully!")
                        st.markdown("**SQL Query Executed:**")
                        # Format for display
                        display_query = f"""
INSERT INTO students 
(first_name, last_name, email, date_of_birth, enrollment_date, gpa, is_active)
VALUES ('{first_name}', '{last_name}', '{email if email else "NULL"}', '{date_of_birth if date_of_birth else "NULL"}', '{enrollment_date}', {gpa}, {is_active})
                        """.strip()
                        st.code(display_query, language='sql')
    
    # TAB 3: Update Student
    with tab3:
        st.header("✏️ Update Student")
        st.markdown("This section demonstrates the **UPDATE** query.")
        
        # Get all students for selection
        query = "SELECT student_id, first_name, last_name, email FROM students ORDER BY last_name, first_name"
        students = execute_query(connection, query, fetch=True)
        
        if students:
            student_options = {
                f"{s['first_name']} {s['last_name']} (ID: {s['student_id']})": s['student_id']
                for s in students
            }
            
            selected_student_label = st.selectbox(
                "Select Student to Update",
                options=list(student_options.keys())
            )
            
            selected_student_id = student_options[selected_student_label]
            
            # Get current student data
            get_student_query = "SELECT * FROM students WHERE student_id = %s"
            current_student = execute_query(connection, get_student_query, params=(selected_student_id,), fetch=True)
            
            if current_student:
                student = current_student[0]
                
                with st.form("update_student_form"):
                    st.markdown(f"**Updating: {student['first_name']} {student['last_name']}**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_first_name = st.text_input("First Name", value=student['first_name'])
                        new_last_name = st.text_input("Last Name", value=student['last_name'])
                        new_email = st.text_input("Email", value=student['email'] or '')
                        new_dob = st.date_input(
                            "Date of Birth",
                            value=student['date_of_birth'] if student['date_of_birth'] else None
                        )
                    
                    with col2:
                        new_enrollment_date = st.date_input(
                            "Enrollment Date",
                            value=student['enrollment_date'] if student['enrollment_date'] else date.today()
                        )
                        new_gpa = st.number_input(
                            "GPA",
                            min_value=0.0,
                            max_value=4.0,
                            value=float(student['gpa']) if student['gpa'] else 0.0,
                            step=0.01,
                            format="%.2f"
                        )
                        new_is_active = st.checkbox("Active Student", value=bool(student['is_active']))
                    
                    updated = st.form_submit_button("💾 Update Student", use_container_width=True)
                    
                    if updated:
                        update_query = """
                        UPDATE students 
                        SET first_name = %s,
                            last_name = %s,
                            email = %s,
                            date_of_birth = %s,
                            enrollment_date = %s,
                            gpa = %s,
                            is_active = %s
                        WHERE student_id = %s
                        """
                        params = (
                            new_first_name,
                            new_last_name,
                            new_email if new_email else None,
                            new_dob if new_dob else None,
                            new_enrollment_date,
                            new_gpa,
                            new_is_active,
                            selected_student_id
                        )
                        
                        result = execute_query(connection, update_query, params=params, fetch=False)
                        
                        if result:
                            st.success(f"✅ Student updated successfully!")
                            st.markdown("**SQL Query Executed:**")
                            display_query = f"""
UPDATE students 
SET first_name = '{new_first_name}',
    last_name = '{new_last_name}',
    email = '{new_email if new_email else "NULL"}',
    date_of_birth = '{new_dob if new_dob else "NULL"}',
    enrollment_date = '{new_enrollment_date}',
    gpa = {new_gpa},
    is_active = {new_is_active}
WHERE student_id = {selected_student_id}
                            """.strip()
                            st.code(display_query, language='sql')
        else:
            st.info("📝 No students found. Add a student first!")
    
    # TAB 4: Delete Student
    with tab4:
        st.header("🗑️ Delete Student")
        st.markdown("This section demonstrates the **DELETE** query.")
        st.warning("⚠️ **Warning:** This action cannot be undone!")
        
        # Get all students for selection
        query = "SELECT student_id, first_name, last_name, email FROM students ORDER BY last_name, first_name"
        students = execute_query(connection, query, fetch=True)
        
        if students:
            student_options = {
                f"{s['first_name']} {s['last_name']} (ID: {s['student_id']})": s['student_id']
                for s in students
            }
            
            selected_student_label = st.selectbox(
                "Select Student to Delete",
                options=list(student_options.keys()),
                key="delete_select"
            )
            
            selected_student_id = student_options[selected_student_label]
            
            # Show student details
            get_student_query = "SELECT * FROM students WHERE student_id = %s"
            current_student = execute_query(connection, get_student_query, params=(selected_student_id,), fetch=True)
            
            if current_student:
                student = current_student[0]
                st.markdown(f"**Student to delete:** {student['first_name']} {student['last_name']}")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("🗑️ Delete Student", type="primary", use_container_width=True):
                        delete_query = "DELETE FROM students WHERE student_id = %s"
                        result = execute_query(connection, delete_query, params=(selected_student_id,), fetch=False)
                        
                        if result:
                            st.success(f"✅ Student '{student['first_name']} {student['last_name']}' deleted successfully!")
                            st.markdown("**SQL Query Executed:**")
                            display_query = f"DELETE FROM students WHERE student_id = {selected_student_id}"
                            st.code(display_query, language='sql')
                            st.rerun()
        else:
            st.info("📝 No students found. Nothing to delete!")
    
    # TAB 5: View Classes
    with tab5:
        st.header("📚 View All Classes")
        st.markdown("This section demonstrates the **SELECT** query on the `classes` table.")
        
        if st.button("🔄 Refresh Class List", key="refresh_classes"):
            st.rerun()
        
        query = "SELECT * FROM classes ORDER BY class_id ASC"
        classes = execute_query(connection, query, fetch=True)
        
        if classes:
            df = pd.DataFrame(classes)
            st.dataframe(df, use_container_width=True)
            st.success(f"✅ Found {len(classes)} class(es)")
            
            # Show the SQL query
            st.markdown("**SQL Query Executed:**")
            st.code(query, language='sql')
        else:
            st.info("📝 No classes found. Add a class using the 'Add Class' tab!")
    
    # TAB 6: Add Class
    with tab6:
        st.header("➕ Add New Class")
        st.markdown("This section demonstrates the **INSERT** query for the `classes` table.")
        
        with st.form("add_class_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                class_name = st.text_input("Class Name *", placeholder="Introduction to SQL")
                class_code = st.text_input("Class Code", placeholder="SQL101", help="Unique code for the class")
                instructor = st.text_input("Instructor", placeholder="Dr. Smith")
            
            with col2:
                credits = st.number_input("Credits", min_value=1, max_value=6, value=3, step=1)
                max_students = st.number_input("Max Students", min_value=1, value=30, step=1)
                semester = st.text_input("Semester", placeholder="Fall 2024")
            
            submitted = st.form_submit_button("➕ Add Class", use_container_width=True)
            
            if submitted:
                if not class_name:
                    st.error("❌ Class Name is required!")
                else:
                    insert_query = """
                    INSERT INTO classes 
                    (class_name, class_code, instructor, credits, max_students, semester)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    params = (
                        class_name,
                        class_code if class_code else None,
                        instructor if instructor else None,
                        credits,
                        max_students,
                        semester if semester else None
                    )
                    
                    result = execute_query(connection, insert_query, params=params, fetch=False)
                    
                    if result:
                        st.success(f"✅ Class '{class_name}' added successfully!")
                        st.markdown("**SQL Query Executed:**")
                        display_query = f"""
INSERT INTO classes 
(class_name, class_code, instructor, credits, max_students, semester)
VALUES ('{class_name}', '{class_code if class_code else "NULL"}', '{instructor if instructor else "NULL"}', {credits}, {max_students}, '{semester if semester else "NULL"}')
                        """.strip()
                        st.code(display_query, language='sql')
    
    # TAB 7: View Enrollments (JOIN)
    with tab7:
        st.header("🔗 View Student Enrollments")
        st.markdown("""
        This section demonstrates **JOIN queries** - combining data from multiple tables!
        Here we'll see students and their enrolled classes together.
        """)
        
        if st.button("🔄 Refresh Enrollments", key="refresh_enrollments"):
            st.rerun()
        
        # JOIN query to get enrollments with student and class names
        join_query = """
        SELECT 
            sc.enrollment_id,
            s.student_id,
            s.first_name,
            s.last_name,
            c.class_id,
            c.class_name,
            c.class_code,
            c.instructor,
            sc.enrollment_date,
            sc.grade,
            sc.status
        FROM student_classes sc
        INNER JOIN students s ON sc.student_id = s.student_id
        INNER JOIN classes c ON sc.class_id = c.class_id
        ORDER BY sc.enrollment_date DESC, s.last_name, s.first_name
        """
        enrollments = execute_query(connection, join_query, fetch=True)
        
        if enrollments:
            df = pd.DataFrame(enrollments)
            st.dataframe(df, use_container_width=True)
            st.success(f"✅ Found {len(enrollments)} enrollment(s)")
            
            st.markdown("---")
            st.markdown("**🔍 Key Learning Points:**")
            st.markdown("""
            - **INNER JOIN**: Combines rows from two tables when there's a match
            - **ON clause**: Specifies how tables are related (foreign key relationship)
            - We're joining:
              - `student_classes` (enrollment table) 
              - WITH `students` (using `student_id`)
              - AND WITH `classes` (using `class_id`)
            - This lets us see student names AND class names together!
            """)
            
            # Show the SQL query
            st.markdown("**SQL Query Executed:**")
            st.code(join_query.strip(), language='sql')
        else:
            st.info("📝 No enrollments found. Enroll a student in a class using the 'Enroll Student' tab!")
            
            st.markdown("---")
            st.markdown("**The JOIN Query Structure:**")
            st.code(join_query.strip(), language='sql')
    
    # TAB 8: Enroll Student in Class
    with tab8:
        st.header("➕ Enroll Student in Class")
        st.markdown("""
        This section demonstrates **INSERT with Foreign Keys**. 
        We're adding a relationship between a student and a class using their IDs.
        """)
        
        # Get students
        students_query = "SELECT student_id, first_name, last_name FROM students ORDER BY last_name, first_name"
        students = execute_query(connection, students_query, fetch=True)
        
        # Get classes
        classes_query = "SELECT class_id, class_name, class_code FROM classes ORDER BY class_name"
        classes = execute_query(connection, classes_query, fetch=True)
        
        if students and classes:
            with st.form("enroll_student_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    student_options = {
                        f"{s['first_name']} {s['last_name']} (ID: {s['student_id']})": s['student_id']
                        for s in students
                    }
                    selected_student_label = st.selectbox(
                        "Select Student *",
                        options=list(student_options.keys())
                    )
                    selected_student_id = student_options[selected_student_label]
                
                with col2:
                    class_options = {}
                    for c in classes:
                        class_code_display = c['class_code'] if c['class_code'] else f"ID: {c['class_id']}"
                        class_label = f"{c['class_name']} ({class_code_display})"
                        class_options[class_label] = c['class_id']
                    selected_class_label = st.selectbox(
                        "Select Class *",
                        options=list(class_options.keys())
                    )
                    selected_class_id = class_options[selected_class_label]
                
                col3, col4 = st.columns(2)
                with col3:
                    enrollment_date = st.date_input("Enrollment Date", value=date.today())
                    grade = st.number_input("Grade (optional)", min_value=0.0, max_value=100.0, value=None, step=0.01, format="%.2f")
                
                with col4:
                    status = st.selectbox("Status", options=["Enrolled", "Completed", "Dropped"], index=0)
                
                enrolled = st.form_submit_button("➕ Enroll Student", use_container_width=True)
                
                if enrolled:
                    insert_query = """
                    INSERT INTO student_classes 
                    (student_id, class_id, enrollment_date, grade, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    params = (
                        selected_student_id,
                        selected_class_id,
                        enrollment_date,
                        grade if grade is not None else None,
                        status
                    )
                    
                    result = execute_query(connection, insert_query, params=params, fetch=False)
                    
                    if result:
                        student_name = [s for s in students if s['student_id'] == selected_student_id][0]
                        class_name = [c for c in classes if c['class_id'] == selected_class_id][0]
                        st.success(f"✅ {student_name['first_name']} {student_name['last_name']} enrolled in {class_name['class_name']}!")
                        st.markdown("**SQL Query Executed:**")
                        display_query = f"""
INSERT INTO student_classes 
(student_id, class_id, enrollment_date, grade, status)
VALUES ({selected_student_id}, {selected_class_id}, '{enrollment_date}', {grade if grade is not None else "NULL"}, '{status}')
                        """.strip()
                        st.code(display_query, language='sql')
                        
                        st.markdown("---")
                        st.markdown("**🔍 Key Learning Points:**")
                        st.markdown("""
                        - We're using **Foreign Keys**: `student_id` and `class_id`
                        - These IDs reference rows in other tables (`students` and `classes`)
                        - The database ensures referential integrity (can't enroll a non-existent student!)
                        - The `UNIQUE` constraint prevents duplicate enrollments (same student, same class)
                        """)
        elif not students:
            st.warning("⚠️ No students found. Please add students first!")
        elif not classes:
            st.warning("⚠️ No classes found. Please add classes first!")
    
    # TAB 9: Table Schema
    with tab9:
        st.header("📖 Database Table Schema")
        st.markdown("""
        This section shows you the structure of all tables and explains relationships, foreign keys, and JOINs.
        """)
        
        # Table selector
        table_selection = st.radio(
            "Select Table to View:",
            ["students", "classes", "student_classes"],
            horizontal=True
        )
        
        schema_query = f"DESCRIBE {table_selection}"
        schema = execute_query(connection, schema_query, fetch=True)
        
        if schema:
            st.markdown(f"### Table Structure: `{table_selection}`")
            df_schema = pd.DataFrame(schema)
            st.dataframe(df_schema, use_container_width=True)
            
            st.markdown("---")
            
            if table_selection == "students":
                st.markdown("### CREATE TABLE Statement:")
                create_table_display = """
CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    date_of_birth DATE,
    enrollment_date DATE DEFAULT (CURRENT_DATE),
    gpa DECIMAL(3, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
                """.strip()
                st.code(create_table_display, language='sql')
            
            elif table_selection == "classes":
                st.markdown("### CREATE TABLE Statement:")
                create_table_display = """
CREATE TABLE classes (
    class_id INT AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(100) NOT NULL,
    class_code VARCHAR(20) UNIQUE,
    instructor VARCHAR(100),
    credits INT DEFAULT 3,
    max_students INT DEFAULT 30,
    semester VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
                """.strip()
                st.code(create_table_display, language='sql')
            
            elif table_selection == "student_classes":
                st.markdown("### CREATE TABLE Statement with Foreign Keys:")
                create_table_display = """
CREATE TABLE student_classes (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    class_id INT NOT NULL,
    enrollment_date DATE DEFAULT (CURRENT_DATE),
    grade DECIMAL(4, 2),
    status VARCHAR(20) DEFAULT 'Enrolled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE,
    UNIQUE KEY unique_enrollment (student_id, class_id)
)
                """.strip()
                st.code(create_table_display, language='sql')
                
                st.markdown("---")
                st.markdown("### 🔑 Key Concepts:")
                st.markdown("""
                **FOREIGN KEY**: Creates a relationship between tables
                - `student_id` references `students(student_id)`
                - `class_id` references `classes(class_id)`
                - **ON DELETE CASCADE**: If a student or class is deleted, their enrollments are automatically deleted
                - **UNIQUE KEY**: Prevents duplicate enrollments (same student in same class twice)
                - This creates a **many-to-many** relationship: Students can have many classes, Classes can have many students
                """)
            
            st.markdown("---")
            st.markdown("### SQL Data Types Explained:")
            
            data_types_info = {
                "INT": "Integer - Stores whole numbers (e.g., student_id: 1, 2, 3...)",
                "AUTO_INCREMENT": "Automatically generates unique sequential numbers for each new row",
                "VARCHAR(n)": "Variable-length string - Stores text up to n characters (e.g., names, emails)",
                "DATE": "Stores dates in YYYY-MM-DD format (e.g., 2024-01-15)",
                "DECIMAL(m,n)": "Fixed-point number - Stores decimal values with precision (e.g., GPA: 3.75)",
                "BOOLEAN": "Stores TRUE (1) or FALSE (0) values",
                "TIMESTAMP": "Stores date and time automatically - CURRENT_TIMESTAMP sets it to now",
                "PRIMARY KEY": "Uniquely identifies each row in the table",
                "FOREIGN KEY": "Creates a link between tables using references to other tables' primary keys",
                "UNIQUE": "Ensures no duplicate values in this column (or combination of columns)",
                "DEFAULT": "Sets a default value if none is provided",
                "NOT NULL": "Requires this field to have a value (cannot be empty)",
                "ON DELETE CASCADE": "When referenced row is deleted, related rows are automatically deleted"
            }
            
            for data_type, description in data_types_info.items():
                st.markdown(f"**{data_type}:** {description}")
            
            st.markdown("---")
            st.markdown("### 🔗 Table Relationships:")
            st.markdown("""
            ```
            students (1) ←→ (many) student_classes (many) ←→ (1) classes
            ```
            
            - One student can be enrolled in many classes
            - One class can have many students
            - The `student_classes` table is a **junction table** that connects students and classes
            - This is called a **many-to-many** relationship
            """)
            
            st.markdown("---")
            st.markdown("**SQL Query Executed:**")
            st.code(schema_query, language='sql')
    
    # Close connection
    if connection:
        connection.close()


if __name__ == "__main__":
    main()

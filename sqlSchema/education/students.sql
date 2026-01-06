-- Students table for education system
CREATE TABLE students (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    date_of_birth DATE,
    enrollment_date DATE DEFAULT CURRENT_DATE,
    major VARCHAR(100),
    gpa DECIMAL(3,2) CHECK (gpa >= 0 AND gpa <= 4.0)
);

-- Sample data
INSERT INTO students (first_name, last_name, email, date_of_birth, major) VALUES
('John', 'Doe', 'john.doe@university.edu', '2000-05-15', 'Computer Science'),
('Jane', 'Smith', 'jane.smith@university.edu', '1999-08-22', 'Mathematics'),
('Bob', 'Johnson', 'bob.johnson@university.edu', '2001-03-10', 'Physics');
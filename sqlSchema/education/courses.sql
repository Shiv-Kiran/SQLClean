-- Courses table
CREATE TABLE courses (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    department VARCHAR(100),
    credits INT CHECK (credits > 0),
    instructor_id INT, -- References instructors table (not created yet)
    semester VARCHAR(20),
    year INT
);

-- Sample data
INSERT INTO courses (course_code, course_name, department, credits, semester, year) VALUES
('CS101', 'Introduction to Computer Science', 'Computer Science', 3, 'Fall', 2024),
('MATH201', 'Calculus II', 'Mathematics', 4, 'Spring', 2024),
('PHYS101', 'Physics I', 'Physics', 4, 'Fall', 2024);
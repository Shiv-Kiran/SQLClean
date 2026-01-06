-- Grades table
CREATE TABLE grades (
    grade_id INT PRIMARY KEY AUTO_INCREMENT,
    enrollment_id INT NOT NULL,
    grade CHAR(2), -- A+, A, B+, etc.
    grade_points DECIMAL(3,2),
    assignment_name VARCHAR(100),
    assignment_date DATE,
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
);

-- Sample data
INSERT INTO grades (enrollment_id, grade, grade_points, assignment_name, assignment_date) VALUES
(1, 'A', 4.0, 'Midterm Exam', '2024-10-15'),
(1, 'A-', 3.7, 'Final Project', '2024-12-10'),
(2, 'B+', 3.3, 'Homework 1', '2024-09-05');
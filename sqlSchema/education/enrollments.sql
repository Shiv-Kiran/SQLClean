-- Enrollments table (many-to-many between students and courses)
CREATE TABLE enrollments (
    enrollment_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    enrollment_date DATE DEFAULT CURRENT_DATE,
    status ENUM('enrolled', 'dropped', 'completed') DEFAULT 'enrolled',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
    UNIQUE(student_id, course_id) -- Prevent duplicate enrollments
);

-- Sample data
INSERT INTO enrollments (student_id, course_id, enrollment_date, status) VALUES
(1, 1, '2024-08-25', 'enrolled'),
(1, 2, '2024-08-25', 'enrolled'),
(2, 2, '2024-08-25', 'enrolled'),
(3, 3, '2024-08-25', 'enrolled');
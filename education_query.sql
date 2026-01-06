SELECT s.first_name, s.last_name, s.major, c.course_name, e.enrollment_date, AVG(g.grade_points) as avg_grade
FROM students s
JOIN enrollments e ON s.student_id = e.student_id
JOIN courses c ON e.course_id = c.course_id
LEFT JOIN grades g ON e.enrollment_id = g.enrollment_id
WHERE s.major = 'Computer Science' AND e.status = 'enrolled'
GROUP BY s.student_id, s.first_name, s.last_name, s.major, c.course_name, e.enrollment_date
HAVING AVG(g.grade_points) > 3.0
ORDER BY s.last_name, c.course_name;
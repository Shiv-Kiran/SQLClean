# Education Database Schema

## Overview
This schema represents a typical university student enrollment system with many-to-many relationships between students and courses.

## Tables
- **students**: Student personal information
- **courses**: Course offerings with details
- **enrollments**: Junction table for student-course relationships
- **grades**: Individual grades for assignments/exams

## Best Practices
- Use foreign keys to maintain referential integrity
- Index frequently queried columns (student_id, course_id)
- Use ENUM for status fields to ensure data consistency
- Consider partitioning grades table by year for large datasets
- Use transactions for enrollment operations to prevent partial updates

## Common Queries
- Student enrollment counts: JOIN students and enrollments
- Course capacity checks: COUNT enrollments per course
- GPA calculations: Aggregate grades with proper weighting
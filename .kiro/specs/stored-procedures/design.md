# Design Document: Stored Procedures for CCICT Helpdesk

## Overview

This design document outlines the implementation of PostgreSQL stored procedures for the CCICT Helpdesk application. The stored procedures will encapsulate database logic, improve security through parameterization, enforce role-based access control at the database level, and optimize performance through reduced network round-trips.

## Architecture

### Layered Architecture

```
Application Layer (Flask/Python)
    ↓ (calls stored procedures)
Database Layer (PostgreSQL)
    ↓ (stored procedures)
Data Layer (Tables, Views, Triggers)
```

### Benefits of Stored Procedures

1. **Security**: Prevents SQL injection by using parameterized inputs
2. **Performance**: Reduces network traffic and query parsing overhead
3. **Maintainability**: Centralizes business logic in the database
4. **Access Control**: Enforces permissions at the database level
5. **Consistency**: Ensures uniform data validation across all clients

## Components and Interfaces

### 1. Ticket Management Procedures


#### sp_create_ticket(p_student_id INT, p_issue TEXT)
- **Purpose**: Create a new ticket with validation
- **Returns**: ticket_id (INT), success (BOOLEAN), message (TEXT)
- **Logic**: Validates student exists, inserts ticket, returns new ID

#### sp_update_ticket_status(p_ticket_id INT, p_status TEXT)
- **Purpose**: Update ticket status (open/resolved)
- **Returns**: success (BOOLEAN), message (TEXT)
- **Logic**: Validates status value, updates ticket, audit log triggered automatically

#### sp_delete_ticket(p_ticket_id INT)
- **Purpose**: Delete a ticket
- **Returns**: success (BOOLEAN), message (TEXT)
- **Logic**: Deletes ticket, audit log triggered automatically

#### sp_get_tickets(p_role TEXT, p_limit INT, p_offset INT)
- **Purpose**: Retrieve tickets with pagination
- **Returns**: TABLE (ticket_id, student_name, issue, status, created_at)
- **Logic**: Joins tickets with students, orders by created_at DESC

### 2. Student Data Procedures

#### sp_get_students(p_role TEXT)
- **Purpose**: Retrieve student records with role-based field masking
- **Returns**: TABLE (id, name, email, phone)
- **Logic**: Returns phone as NULL for support_role, full data for admin

#### sp_get_student_by_id(p_student_id INT, p_role TEXT)
- **Purpose**: Retrieve single student with role-based access
- **Returns**: TABLE (id, name, email, phone)
- **Logic**: Similar to sp_get_students but for single record

### 3. Dashboard Statistics Procedures

#### sp_get_admin_dashboard_stats()
- **Purpose**: Calculate admin dashboard metrics
- **Returns**: TABLE (total_students, total_tickets, total_staff, last_ticket_date)
- **Logic**: Performs COUNT aggregations and MAX date in single query

#### sp_get_support_dashboard_stats()
- **Purpose**: Calculate support dashboard metrics
- **Returns**: TABLE (open_tickets, resolved_tickets, total_students)
- **Logic**: Counts tickets by status and total students

### 4. Audit Log Procedures

#### sp_get_audit_logs(p_limit INT, p_offset INT)
- **Purpose**: Retrieve audit logs with pagination
- **Returns**: TABLE (id, action, student_id, old_issue, new_issue, changed_at)
- **Logic**: Returns logs ordered by changed_at DESC

#### sp_get_audit_logs_filtered(p_action TEXT, p_student_id INT, p_start_date TIMESTAMP, p_end_date TIMESTAMP)
- **Purpose**: Retrieve filtered audit logs
- **Returns**: TABLE (id, action, student_id, old_issue, new_issue, changed_at)
- **Logic**: Applies WHERE clauses based on non-null parameters

### 5. Authentication Procedures

#### sp_authenticate_user(p_username TEXT, p_password TEXT)
- **Purpose**: Validate user credentials
- **Returns**: TABLE (user_id, username, role, authenticated)
- **Logic**: Checks username exists, verifies bcrypt hash, returns user data without password

#### sp_update_user_password(p_user_id INT, p_new_password_hash TEXT)
- **Purpose**: Update user password hash
- **Returns**: success (BOOLEAN), message (TEXT)
- **Logic**: Updates password field for specified user

### 6. Search and Filter Procedures

#### sp_search_tickets(p_search_term TEXT, p_status TEXT, p_limit INT)
- **Purpose**: Search tickets by issue text and/or status
- **Returns**: TABLE (ticket_id, student_name, issue, status, created_at)
- **Logic**: Uses ILIKE for case-insensitive search, optional status filter

#### sp_get_tickets_by_student(p_student_id INT)
- **Purpose**: Get all tickets for a specific student
- **Returns**: TABLE (ticket_id, issue, status, created_at)
- **Logic**: Filters tickets by student_id

### 7. Batch Operations Procedures

#### sp_batch_resolve_tickets(p_ticket_ids INT[])
- **Purpose**: Mark multiple tickets as resolved
- **Returns**: success (BOOLEAN), updated_count (INT), message (TEXT)
- **Logic**: Updates all tickets in array, wrapped in transaction

#### sp_batch_delete_tickets(p_ticket_ids INT[])
- **Purpose**: Delete multiple tickets
- **Returns**: success (BOOLEAN), deleted_count (INT), message (TEXT)
- **Logic**: Deletes all tickets in array, wrapped in transaction

### 8. Staff Management Procedures

#### sp_get_staff_users()
- **Purpose**: Retrieve all staff users
- **Returns**: TABLE (id, username, role)
- **Logic**: Returns staff without password hashes

#### sp_create_staff_user(p_username TEXT, p_password_hash TEXT, p_role TEXT)
- **Purpose**: Create new staff user
- **Returns**: user_id (INT), success (BOOLEAN), message (TEXT)
- **Logic**: Validates unique username, inserts user

## Data Models

### Input/Output Structures

```sql
-- Standard Response Type
TYPE sp_response AS (
    success BOOLEAN,
    message TEXT,
    data JSONB
);

-- Ticket Record Type
TYPE ticket_record AS (
    ticket_id INT,
    student_name TEXT,
    issue TEXT,
    status TEXT,
    created_at TIMESTAMP
);

-- Dashboard Stats Type
TYPE dashboard_stats AS (
    stat_name TEXT,
    stat_value BIGINT
);
```

## Error Handling

### Error Codes and Messages

- **23503**: Foreign key violation (invalid student_id)
- **23505**: Unique constraint violation (duplicate username)
- **22001**: String data too long (issue text exceeds limit)
- **P0001**: Custom validation error (invalid status value)
- **P0002**: No data found (ticket/student not found)

### Exception Handling Pattern

```sql
BEGIN
    -- Operation logic
EXCEPTION
    WHEN foreign_key_violation THEN
        RETURN QUERY SELECT false, 'Invalid student ID', NULL::JSONB;
    WHEN unique_violation THEN
        RETURN QUERY SELECT false, 'Username already exists', NULL::JSONB;
    WHEN OTHERS THEN
        RETURN QUERY SELECT false, 'An unexpected error occurred', NULL::JSONB;
END;
```

## Testing Strategy

### Unit Testing
- Test each stored procedure with valid inputs
- Test with invalid inputs (NULL, empty strings, invalid IDs)
- Test boundary conditions (max length strings, large numbers)

### Integration Testing
- Test stored procedures called from Python application
- Verify role-based access control works correctly
- Test transaction rollback on errors

### Performance Testing
- Measure execution time with varying dataset sizes
- Test with 100, 1000, 10000 records
- Ensure dashboard stats complete within 500ms

### Security Testing
- Attempt SQL injection through parameters
- Verify password hashes are never returned
- Test role escalation attempts

## Implementation Notes

### PostgreSQL Version
- Requires PostgreSQL 12 or higher
- Uses PL/pgSQL procedural language
- Leverages JSONB for flexible return types

### Migration Strategy
1. Create all stored procedures in database
2. Update Python code to call procedures instead of direct queries
3. Test thoroughly in development environment
4. Deploy to production with rollback plan
5. Monitor performance and error logs

### Backward Compatibility
- Keep existing direct SQL queries during transition
- Gradually replace with stored procedure calls
- Maintain both approaches until fully tested

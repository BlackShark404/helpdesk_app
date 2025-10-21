SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Drop tables to ensure a clean slate
--
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS staff_users;

--
--
CREATE TABLE public.staff_users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE public.students (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT
);

CREATE TABLE public.tickets (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES public.students(id),
    issue TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

--
--
INSERT INTO public.staff_users (username, password, role) VALUES
('admin', 'adminpass123', 'admin'),
('support_staff', 'supportpass', 'support_role'),
('it_support', 'itsupportpass', 'support_role');

INSERT INTO public.students (name, email, phone) VALUES
('Juan Dela Cruz', 'juan.delacruz@ctu.edu.ph', '555-1234'),
('Pedro Macaraig', 'pedro.macaraig@ctu.edu.ph', '555-5678'),
('Maria Dizcaya', 'maria.dizcaya@ctu.edu.ph', '555-9012');

INSERT INTO public.tickets (student_id, issue) VALUES
(1, 'Cannot login to online portal.'),
(2, 'Laptop won''t connect to CTU Free WiFi.'),
(1, 'Password reset request.'),
(3, 'CTU account phone number is no longer active.');

-- Phase 1: for checking
SELECT id, username, password FROM public.staff_users;


--phase 2

DROP ROLE IF EXISTS support_role;
DROP ROLE IF EXISTS admin_role;
DROP ROLE IF EXISTS support_user;
DROP ROLE IF EXISTS admin_user;

-- Create the main roles
CREATE ROLE support_role;
CREATE ROLE admin_role;

-- Create specific users for testing
CREATE USER support_user WITH PASSWORD 'support123';
CREATE USER admin_user WITH PASSWORD 'admin123';

-- Grant role memberships
GRANT support_role TO support_user;
GRANT admin_role TO admin_user;

-- Restricted view for support staff (hide phone unless admin)
CREATE OR REPLACE VIEW public.students_support_view AS
SELECT 
    id,
    name,
    email,
    CASE 
        WHEN pg_has_role(current_user, 'admin_role', 'MEMBER') 
            THEN phone
        ELSE NULL::text  -- must return the same type
    END AS phone
FROM public.students;

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;

GRANT CONNECT ON DATABASE helpdesk_dump TO support_role;
GRANT CONNECT ON DATABASE helpdesk_dump TO admin_role;
GRANT USAGE ON SCHEMA public TO support_role;
GRANT USAGE ON SCHEMA public TO admin_role;
GRANT SELECT ON public.students_support_view TO support_role;
GRANT SELECT ON public.tickets TO support_role;
GRANT SELECT ON public.staff_users TO support_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin_role;


SET ROLE support_user;
SELECT * FROM public.students_support_view;
-- SELECT phone FROM public.students;

RESET ROLE;

SET ROLE admin_user;
SELECT * FROM public.students_support_view;

SELECT * FROM public.tickets;

--phase 3

RESET ROLE;

-- ========================================================
-- Phase 3: Auditing and Logging
-- ========================================================

-- Create the audit_log table (must be run as admin)
CREATE TABLE IF NOT EXISTS public.audit_log (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,            -- INSERT / UPDATE / DELETE
    student_id INT NOT NULL,         -- linked student id
    old_issue TEXT,                  -- previous issue value
    new_issue TEXT,                  -- new issue value
    changed_at TIMESTAMP DEFAULT now()
);

-- Function for logging ticket changes
CREATE OR REPLACE FUNCTION public.log_ticket_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO public.audit_log (action, student_id, new_issue)
        VALUES ('INSERT', NEW.student_id, NEW.issue);
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO public.audit_log (action, student_id, old_issue, new_issue)
        VALUES ('UPDATE', NEW.student_id, OLD.issue, NEW.issue);
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO public.audit_log (action, student_id, old_issue)
        VALUES ('DELETE', OLD.student_id, OLD.issue);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to tickets table
DROP TRIGGER IF EXISTS tickets_audit_trigger ON public.tickets;

CREATE TRIGGER tickets_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON public.tickets
FOR EACH ROW
EXECUTE FUNCTION public.log_ticket_changes();

-- ========================================================
-- Testing Phase 3
-- ========================================================
-- Insert new ticket
INSERT INTO public.tickets (student_id, issue)
VALUES (1, 'Test new issue for audit');

-- Update a ticket (make sure the ID exists)
UPDATE public.tickets
SET issue = 'Chairs are ruined'
WHERE id = 1;

-- Delete a ticket (make sure the ID exists)
DELETE FROM public.tickets WHERE id = 2;

-- Check results
SELECT * FROM public.tickets;
SELECT * FROM public.audit_log;

-- ========================================================
-- Phase 4: Stored Procedure - Add New Student
-- ========================================================

CREATE OR REPLACE PROCEDURE public.add_new_student(
    p_name TEXT,
    p_email TEXT,
    p_phone TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate inputs
    IF p_name IS NULL OR TRIM(p_name) = '' THEN
        RAISE EXCEPTION 'Student name cannot be empty';
    END IF;
    
    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        RAISE EXCEPTION 'Student email cannot be empty';
    END IF;
    
    -- Insert the new student
    INSERT INTO public.students (name, email, phone)
    VALUES (p_name, p_email, p_phone);
    
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'Student with email % already exists', p_email;
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Error adding student: %', SQLERRM;
END;
$$;

-- ========================================================
-- Testing the stored procedure
-- ========================================================
-- Test 1: Add a new student with phone
CALL public.add_new_student('Test Student', 'test.student@ctu.edu.ph', '555-9999');

-- Test 2: Add a new student without phone
CALL public.add_new_student('Another Student', 'another.student@ctu.edu.ph', NULL);

-- Verify the additions
SELECT * FROM public.students WHERE email LIKE '%test%' OR email LIKE '%another%';
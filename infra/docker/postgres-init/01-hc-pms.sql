-- Harbourfront Capital's legacy PMS gets its own database and login.
-- ResearchPilot never uses these credentials; it integrates through the PMS API (and, later, a read-only role).
CREATE USER hc WITH PASSWORD 'hc' CREATEDB;
CREATE DATABASE hc_pms OWNER hc;

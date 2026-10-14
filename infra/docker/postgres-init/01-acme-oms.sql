-- Acme Market's legacy OMS gets its own database and login.
-- OpsPilot never uses these credentials; it integrates through the OMS API (and, later, a read-only role).
CREATE USER acme WITH PASSWORD 'acme' CREATEDB;
CREATE DATABASE acme_oms OWNER acme;

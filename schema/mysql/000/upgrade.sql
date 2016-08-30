
CREATE DATABASE olassc;

-- Create the user and grant privileges
CREATE USER 'olassc'@'%' IDENTIFIED BY 'insecurepassword';

FLUSH PRIVILEGES;

GRANT
    ALL PRIVILEGES
ON
    olassc.*
TO
    'olassc'@'%';

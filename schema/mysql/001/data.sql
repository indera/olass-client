
INSERT INTO gender
    (gender, gender_name, gender_description)
VALUES
    ('A', 'Ambiguous', 'May be used for individuals who are physically undifferentiaded from birth'),
    ('F',  'Female', ''),
    ('M',  'Male', ''),
    ('NI', 'No information', ''),
    ('UN', 'Unknown', ''),
    ('OT', 'Other', 'May ne used for individuals who are undergoing gender re-assignment')
;


INSERT INTO patient
    (pat_mrn, pat_birth_date, pat_first_name, pat_last_name, pat_address_city, pat_address_zip)
VALUES
    ('mrn_001', '1950-01-01', 'Abc', 'Def', 'Gainesville', '32606'),
    ('mrn_002', '1950-01-01', 'Abc', 'Def', 'Gainesville', '32607')
;

SHOW TABLES;
/*
SELECT * FROM version;
SELECT * FROM gender;
*/
SELECT pat_mrn, pat_birth_date, pat_first_name, pat_last_name, pat_address_city, pat_address_zip FROM patient;

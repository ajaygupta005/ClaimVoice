-- Synthetic cardiology providers near Midtown Manhattan (40.7580, -73.9855) so the
-- canonical "find a cardiologist near me" demo returns results. The base synthetic
-- NPPES sample has no cardiology specialty. Idempotent via ON CONFLICT (npi).
-- specialty_codes include "Cardiologist" so the app-side substring match in
-- services/geo_search.py matches the extracted query term.
INSERT INTO providers
  (id, npi, first_name, last_name, taxonomy_code, taxonomy_description, specialty_codes,
   practice_location_address_line_1, practice_location_city, practice_location_state,
   practice_location_zip, practice_location_phone, accepting_new_patients, quality_rating,
   hospital_name, location, audit_source)
VALUES
  (gen_random_uuid(), 'CARD000001', 'Maria', 'Reyes', '207RC0000X', 'Cardiology',
   ARRAY['Cardiology','Cardiologist','Cardiovascular Disease'],
   '120 E 56th St', 'New York', 'NY', '10022', '(212) 555-0110', true, 4.8,
   'Midtown Heart Center', ST_GeogFromText('SRID=4326;POINT(-73.9740 40.7610)'), 'seed_cardiology'),
  (gen_random_uuid(), 'CARD000002', 'David', 'Okafor', '207RC0000X', 'Cardiology',
   ARRAY['Cardiology','Cardiologist','Cardiovascular Disease'],
   '425 W 59th St', 'New York', 'NY', '10019', '(212) 555-0111', true, 4.6,
   'Columbus Circle Cardiology', ST_GeogFromText('SRID=4326;POINT(-73.9870 40.7690)'), 'seed_cardiology'),
  (gen_random_uuid(), 'CARD000003', 'Priya', 'Nair', '207RC0000X', 'Cardiology',
   ARRAY['Cardiology','Cardiologist','Cardiovascular Disease'],
   '300 Park Ave', 'New York', 'NY', '10022', '(212) 555-0112', true, 4.9,
   'Park Avenue Cardiovascular', ST_GeogFromText('SRID=4326;POINT(-73.9720 40.7570)'), 'seed_cardiology'),
  (gen_random_uuid(), 'CARD000004', 'James', 'Whitfield', '207RC0000X', 'Cardiology',
   ARRAY['Cardiology','Cardiologist','Cardiovascular Disease'],
   '55 W 46th St', 'New York', 'NY', '10036', '(212) 555-0113', false, 4.3,
   'Rockefeller Heart Associates', ST_GeogFromText('SRID=4326;POINT(-73.9830 40.7570)'), 'seed_cardiology'),
  (gen_random_uuid(), 'CARD000005', 'Sofia', 'Marino', '207RC0000X', 'Cardiology',
   ARRAY['Cardiology','Cardiologist','Cardiovascular Disease'],
   '1 Gustave L Levy Pl', 'New York', 'NY', '10029', '(212) 555-0114', true, 4.7,
   'Mount Sinai Cardiology', ST_GeogFromText('SRID=4326;POINT(-73.9520 40.7900)'), 'seed_cardiology'),
  (gen_random_uuid(), 'CARD000006', 'Henry', 'Cho', '207RC0000X', 'Cardiology',
   ARRAY['Cardiology','Cardiologist','Cardiovascular Disease'],
   '200 W 57th St', 'New York', 'NY', '10019', '(212) 555-0115', true, 4.5,
   'Carnegie Hall Cardiology', ST_GeogFromText('SRID=4326;POINT(-73.9810 40.7650)'), 'seed_cardiology')
ON CONFLICT (npi) DO NOTHING;

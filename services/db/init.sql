CREATE EXTENSION IF NOT EXISTS vector;
-- Optional: create a database table using the vector type
CREATE TABLE IF NOT EXISTS example_table (
    id SERIAL PRIMARY KEY,
    embedding VECTOR(3)
);

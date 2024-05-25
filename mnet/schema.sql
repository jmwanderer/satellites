CREATE TABLE targets (
  address TEXT not NULL PRIMARY KEY,
  name TEXT not NULL,
  run BOOLEAN DEFAULT TRUE,
  running BOOLEAN DEFAULT FALSE,
  updated INTEGER  DEFAULT 0,
  responded BOOLEAN DEFAULT FALSE,
  total_count INTEGER DEFAULT 0,
  total_success INTEGER DEFAULT 0
);


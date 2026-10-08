# Backend test environment

pytest must fail closed if the explicit test environment is not configured.

The test process does not load `backend/.env` or `frontend/.env`. Export the
three variables in the shell before pytest. Do not point pytest at production.

Development application (unchanged):

- MongoDB: `mongodb://localhost:27017`
- Database: `propmanage_db`
- API: `localhost:8001`

Isolated test environment:

- `REACT_APP_BACKEND_URL=http://localhost:8002`
- `MONGO_URL=mongodb://localhost:27017`
- `DB_NAME=propmanage_test`

Production, including `propmanage.ro`, is never a pytest target.
Emergent preview hosts are never a pytest target.

`backend/db.py` remains the only database client. Pytest does not create a
second client. The three variables must be exported before pytest imports that
module. Application startup still reads `backend/.env` for the development
process; that load does not override variables already set in the environment.

A directory-wide pytest run stays refused while some test files still bypass
this contract. Those files are listed by the gate and are not imported.

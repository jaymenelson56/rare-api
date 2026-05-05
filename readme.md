
## Running Tests

1. Start the database
   ```
   docker-compose up -d
   ```

2. Grant the test-database permission to `rare_user` *(one-time setup — requires a Postgres superuser)*
   ```
   sudo -u postgres psql -c "ALTER USER rare_user CREATEDB;"
   ```

3. Install dev dependencies
   ```
   pipenv install --dev
   ```

4. Run all tests
   ```
   pipenv run pytest
   ```

5. Run a specific test file
   ```
   pipenv run pytest rareapi/tests/test_profile_post_count.py -v
   ```

### FAQs

1. How are test identified in test files?
- The test methods are identified by convention when using pytest. Any method which has `test` prefix is considered a test
 to be executed. Refer: https://pytest.org/latest/goodpractices.html#test-discovery 
 
2. What are the types of Transactions?
- 

3. What are the types of stores?
- In-Memory transaction stores, Ledgers, Graph stores. (Jason or Lovesh to elaborate this and also add reference 
to files having implementation of these stores. Probably `persistence/chain_store.py` etc.)

4. How are the fixtures organised?
- The fixtures common to multiple suites are added to `conftest.py` under the test folder and those specific to the 
suites are added to the suite itself

5. Why do we have to save Merkel info to DB and not log file itself?

6. What is the difference between Sovrin and Plenum? (In terms of use case, why we have 2?)

7. 
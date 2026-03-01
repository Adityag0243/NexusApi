
## Question 1. Why does the credit system use a transaction ledger instead of a balance column?

Answer 1: If we just put one column for balance we might face the issue of **race condition**. Let suppose one of the user using the credit ( i.e. spending x credits ) at the same time admin is trying to add credit ( i.e. adding y credits ) now these operations are happening at the same time and at the same memory block so there is a **chance of data corruption**, which can cause either the organization loose the more credit or gain more credit than expected.

Example : current balance == 100
operation 1 : user spending 10 credits
operation 2 : admin adding 50 credits

*(one operation == 3 atomic steps ==> 1. read current balance, 2. perform operation, 3. update balance)*

total 6 atomic steps and they can *overlap* each other

### one of the possible order of execution is as follows
- Both operations read the same balance = 100
- operation 1 perform operation = 100 - 10 = 90
- operation 2 perform operation = 100 + 50 = 150
- operation 1 update balance = 90
- operation 2 update balance = 150

> so final balance equals 150 but actual balance must be equal to 140.

**So we use transaction ledger to keep track of all the transactions and at the end we can calculate the balance.**
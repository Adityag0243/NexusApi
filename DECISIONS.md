
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

**So we use transaction ledger to keep track of all the transactions and at the end we can calculate the balance let say using SUM() function.**

> Trade-off: While calculating SUM() is computationally heavier than reading a single column, PostgreSQL handles this efficiently with indexing. At massive scale, this could be optimized using daily snapshots like every night calculate the sum of all transactions and store it in a column next day start fresh appending + previous day's total.



## Question 2 / R5. What happens if deduct_credits is called twice simultaneously for the same organisation with exactly enough credits for one call?  / simultaneous credit deduction problem.

Answer R5: I am using **with_for_update()** in *credit_service.py* for **ROW LEVEL LOCK** so that no other transaction can modify the row until the current transaction is complete other simultaneous transactions will wait for the current transaction to complete so there will be no ambiguity in the final balance.

> Trade-off: This will prevent other transactions from modifying the row until the current transaction is complete. But it will also prevent other transactions from reading the row until the current transaction is complete.

## Question R6. What happens if the deduction succeeds but the processing fails? Credits were spent but no result was returned.

Answer R6: So there are two possible ways to handle this situation:

1. **Lock till end**: Instead of locking the db just for the duration of the transaction, we can lock the db till the ai report is not generated and we are sure that we can return the result to the user. This will prevent other transactions from modifying the row until the current transaction is complete.
>But our actual AI processesing is pretty heavy and it might take a lot of time so we don't want to lock the db for that long.

2. **Refund the credits**: First we will deduct the credits and commit the transaction immediately to release the lock so other users can keep working. Parallely we will do the ai processing. If the AI processing crashes later, we catch the error and issue a new +25 transaction as a "Refund". 

> I am going with the second approach because it is more common and it is also more flexible and not locking the db for a long time.


## Question 3. What happens when the background worker fails after credits have been deducted?
Answer 3: For now i just use try and except block and if worker fails i simply refund the credits. But this is not a very good approach to it. Other approach which i feel is good enough is following:

1. Simply retry the task 2-3 times with some intervals and if it fails again then refund the credits.
2. Dead Letter Queue (DLQ)instead of refunding immediately move the job to a special queue called the DLQ, now admin can manually or using some script needs to review those failed jobs and decide whether to refund or not.
> this is important because sometimes the ai might be down for maintenance and we don't want to refund the credits immediately or let say user put his/her efforts for the /summarise endpoint and we simply can't refund the credits.
3. Let say our system is working fine but suddenly AI provider goes down and if multiple consecutive failures happen then stop picking up new jobs from the queue entirely and immediately refunds everyone until the AI provider comes back online.

> For now i use a simpler logic of just refunding the credits after one failure.

## R8. What happens if Redis is unavailable? Does the entire API go down, or does it fail open (allow all requests)? 

Answer R8: The API is configured to "fail open", meaning it will bypass the rate limit checks and allow all requests if Redis goes down.

> Justification: Rate limiting is secondary resource for protecting our primary resource ( AI processing ) from abuse. Just because rate limiting is down we should not stop our primary resource from working. By failing open, the application remains highly available during such secondary resource failure.
> The temporary trade-off is higher potential load or abuse, which is a better alternative than failing to fulfill legitimate AI processing requests that the organization has already paid credits for. 

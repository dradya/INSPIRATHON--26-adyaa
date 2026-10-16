# Lecture 14: Recursion, Recurrence Relations & Dynamic Programming

## 1. Fundamental Principles of Recursion
Recursion solves complex problems by decomposing them into smaller, self-similar subproblems:
- **Base Case**: The terminating condition that prevents infinite stack frames (e.g., `if n <= 1: return 1`).
- **Recursive Step**: Reducing the problem size toward the base case (`fib(n-1) + fib(n-2)`).
- **Tail Recursion**: Optimization where the recursive call is the final operation in the function frame.

## 2. Analyzing Recursion Trees & Master Theorem
For divide-and-conquer recurrences of the form `T(n) = aT(n/b) + f(n)`:
- Binary Search: `T(n) = T(n/2) + O(1)` -> `O(log n)`
- Merge Sort: `T(n) = 2T(n/2) + O(n)` -> `O(n log n)`
- Karatsuba Multiplication: `T(n) = 3T(n/2) + O(n)` -> `O(n^1.585)`

## 3. From Naive Recursion to Memoization
Naive recursion on overlapping subproblems leads to exponential `O(2^n)` blowup.
By caching intermediate results in a lookup table (memoization) or bottom-up tabulation, we reduce time complexity to polynomial `O(n)`.

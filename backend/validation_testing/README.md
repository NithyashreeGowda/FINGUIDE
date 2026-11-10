# Financial Variable Validation and Formula Verification

## Project
**FINGUIDE – Intelligent AI Financial Advisor for Context-Aware, Risk-Aware and Evidence-Grounded Investment Decision Support**

## Individual Contribution
My contribution focuses on validating financial variables, verifying financial formulas, and testing numerical accuracy in the FINGUIDE project.

## Objectives
- Verify the accuracy of financial calculations.
- Test financial formulas using sample input values.
- Identify invalid numerical inputs.
- Check calculations involving negative, small, and large values.
- Improve confidence in the numerical outputs of the financial calculator.

## Testing Areas

1. **Formula Verification:** Tested Quick Ratio, Interest Coverage, Free Cash Flow, EPS, Dividend Yield, Growth, and CAGR.
2. **Input Validation:** Checked how the calculator handles missing, non-numeric, NaN, and infinite values.
3. **Boundary Testing:** Tested negative cash flow, small EPS values, large financial values, and declining growth.
4. **Numerical Accuracy:** Used `pytest.approx()` to verify calculated results with suitable precision.

## Tools and Technologies
- Python 3.13
- Pytest
- VS Code
- Financial Calculator Module

## Test Execution

Run the following command from the backend folder:

```powershell
python -m pytest .\validation_testing\test_formula_verification.py -v
```

## Test Results

**Total test cases: 16**

**Passed: 16**

**Failed: 0**

All 16 tests passed successfully.

## Conclusion
The testing confirms that the selected financial calculations produce the expected results for the tested inputs. Invalid inputs are also checked to ensure they are rejected appropriately. This contribution supports the numerical accuracy and reliability of the FINGUIDE financial calculator.
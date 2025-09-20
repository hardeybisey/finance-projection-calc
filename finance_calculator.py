import streamlit as st
import math

st.set_page_config(page_title="Finance Projection Calculator", layout="wide")

st.title("🏠🚗 Personal Finance Projection Calculator")

# Mode
mode = st.radio("Select mode:", ["House Purchase", "Car Purchase"])

# Inputs
st.sidebar.header("Inputs")

price = st.sidebar.number_input("Price (£)", min_value=0, value=300000, step=1000)
deposit_percent = st.sidebar.number_input("Deposit (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5)
deposit_amount_override = st.sidebar.number_input("Deposit amount (£)", min_value=0, value=0, step=1000)
interest_rate = st.sidebar.number_input("Interest rate (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.1)
term_years = st.sidebar.number_input("Term (years)", min_value=1, max_value=40, value=25, step=1)
arrangement_fee = st.sidebar.number_input("Arrangement fee (£)", min_value=0, value=1000, step=100)
legal_fees = st.sidebar.number_input("Conveyancing & Legal fees (£)", min_value=0, value=1500, step=100) if mode == "House Purchase" else 0
monthly_overheads = st.sidebar.number_input("Monthly overhead costs (£)", min_value=0, value=500, step=50)
monthly_expenses = st.sidebar.number_input("Other monthly expenses (£)", min_value=0, value=1000, step=50)
loan_to_income_ratio = st.sidebar.number_input("Loan-to-Income ratio (e.g. 4.5)", min_value=1.0, max_value=10.0, value=4.5, step=0.1)
net_monthly_salary = st.sidebar.number_input("Net monthly salary (£)", min_value=0, value=3000, step=100)
tax_pct = st.sidebar.number_input("Effective tax rate (%)", min_value=0.0, max_value=100.0, value=35.0, step=0.5)

# Calculations
deposit_amount = deposit_amount_override if deposit_amount_override > 0 else price * deposit_percent / 100
mortgage_amount = price - deposit_amount
ltv = (mortgage_amount / price) * 100 if price > 0 else 0

monthly_rate = (interest_rate / 100) / 12
n_payments = term_years * 12
if monthly_rate > 0:
    monthly_payment = mortgage_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
else:
    monthly_payment = mortgage_amount / n_payments

annual_payment = monthly_payment * 12

# From net salary
net_annual_salary = net_monthly_salary * 12
gross_annual_salary = net_annual_salary / (1 - tax_pct / 100) if tax_pct < 100 else net_annual_salary

# Required incomes
min_gross_by_lti = mortgage_amount / loan_to_income_ratio if loan_to_income_ratio > 0 else 0
min_gross_by_afford = ((monthly_payment + monthly_overheads + monthly_expenses) * 12) / (1 - tax_pct / 100) if tax_pct < 100 else 0
suggested_min_gross = max(min_gross_by_lti, min_gross_by_afford)

# Output
st.subheader("Results")
col1, col2 = st.columns(2)

with col1:
    st.metric("House/Car Price (£)", f"{price:,.0f}")
    st.metric("Deposit (£)", f"{deposit_amount:,.0f}")
    st.metric("Mortgage/Loan Amount (£)", f"{mortgage_amount:,.0f}")
    st.metric("Loan-to-Value (%)", f"{ltv:.1f}%")
    st.metric("Monthly Mortgage/Loan Payment (£)", f"{monthly_payment:,.0f}")
    st.metric("Annual Mortgage/Loan Payment (£)", f"{annual_payment:,.0f}")

with col2:
    st.metric("Net Monthly Salary (£)", f"{net_monthly_salary:,.0f}")
    st.metric("Net Annual Salary (£)", f"{net_annual_salary:,.0f}")
    st.metric("Est. Gross Annual Salary (£)", f"{gross_annual_salary:,.0f}")
    st.metric("Min Gross Income Required (LTI)", f"{min_gross_by_lti:,.0f}")
    st.metric("Min Gross Income Required (Afford)", f"{min_gross_by_afford:,.0f}")
    st.metric("Suggested Min Gross Income (£)", f"{suggested_min_gross:,.0f}")

# Fees
if mode == "House Purchase":
    st.info(f"One-off fees: Arrangement £{arrangement_fee:,.0f} + Legal £{legal_fees:,.0f} = £{arrangement_fee + legal_fees:,.0f}")
else:
    st.info(f"One-off fees: Arrangement £{arrangement_fee:,.0f}")

# Footer
st.caption("💡 Net salary is primary input. Gross salary is estimated using the flat effective tax rate. Adjust 'Effective tax rate' to match your situation.")

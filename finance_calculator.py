import streamlit as st
import math

st.set_page_config(page_title="Finance Projection Calculator", layout="centered")

st.title("🏠🚗 Personal Finance Projection Calculator")

st.write("Use this tool to estimate either the **salary required** for a target house/car, "
         "or the **maximum price you can afford** given your current salary and expenses.")

# Tabs for House and Car
tab1, tab2 = st.tabs(["🏠 House", "🚗 Car"])

def monthly_payment(principal, annual_rate, years):
    r = annual_rate / 100 / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

def required_salary(mortgage_amount, monthly_payment, monthly_expenses, lti, tax_rate):
    # Method 1: LTI
    gross_lti = mortgage_amount / lti if lti > 0 else 0
    # Method 2: Affordability (net → gross)
    needed_net_monthly = monthly_payment + monthly_expenses
    gross_afford = (needed_net_monthly * 12) / (1 - tax_rate / 100) if tax_rate < 100 else 0
    return gross_lti, gross_afford, max(gross_lti, gross_afford)

def affordable_price(net_monthly_salary, monthly_expenses, deposit_pct, rate, term, lti, tax_rate):
    # Net → Gross
    net_annual = net_monthly_salary * 12
    gross_annual = net_annual / (1 - tax_rate / 100) if tax_rate < 100 else net_annual

    # Max mortgage by affordability (payment must fit in net)
    available_for_mortgage = max(0, net_monthly_salary - monthly_expenses)
    # Solve approx: assume affordable mortgage is available_for_mortgage * term
    affordable_mortgage = available_for_mortgage * 12 * term  

    # Max mortgage by LTI
    affordable_by_lti = gross_annual * lti

    # Take the lower (conservative)
    max_mortgage = min(affordable_mortgage, affordable_by_lti)
    price = max_mortgage / (1 - deposit_pct / 100)
    return price, gross_annual, net_annual

# --- HOUSE ---
with tab1:
    st.header("🏠 House Calculator")
    subtab1, subtab2 = st.tabs(["📈 Salary Projection", "💰 Affordability"])

    with subtab1:
        st.subheader("How much salary do I need for this house?")
        price = st.number_input("House price (£)", value=300000, step=5000, help="Target house price.", key="a")
        deposit_pct = st.slider("Deposit (%)", 0, 50, 15, help="Percent of price you’ll pay upfront.", key="b")
        rate = st.number_input("Mortgage interest rate (%)", value=5.0, step=0.1, key="c")
        term = st.slider("Mortgage term (years)", 1, 40, 25, key="d")
        lti = st.number_input("Loan-to-Income multiple", value=4.5, step=0.1, help="Bank multiple of gross salary.", key="e")
        monthly_expenses = st.number_input("Monthly expenses (£)", value=1500, step=100, key="f")
        tax_rate = st.slider("Effective tax rate (%)", 0, 60, 35, key="g")

        deposit = price * deposit_pct / 100
        mortgage = price - deposit
        pay = monthly_payment(mortgage, rate, term)

        gross_lti, gross_afford, gross_needed = required_salary(mortgage, pay, monthly_expenses, lti, tax_rate)

        st.success(f"💡 Required Gross Annual Salary: **£{gross_needed:,.0f}**")
        st.write(f"- By Loan-to-Income: £{gross_lti:,.0f}") 
        st.write(f"- By Affordability: £{gross_afford:,.0f}")
        st.write(f"Monthly payment ≈ £{pay:,.0f}")

    with subtab2:
        st.subheader("How much house can I afford?")
        net_monthly = st.number_input("Net monthly salary (£)", value=3000, step=100, key="h")
        monthly_expenses = st.number_input("Monthly expenses (£)", value=1500, step=100, key="i")
        deposit_pct = st.slider("Deposit (%)", 0, 50, 15, key="j")
        rate = st.number_input("Mortgage interest rate (%)", value=5.0, step=0.1, key="k")
        term = st.slider("Mortgage term (years)", 1, 40, 25, key="l")
        lti = st.number_input("Loan-to-Income multiple", value=4.5, step=0.1, key="m")
        tax_rate = st.slider("Effective tax rate (%)", 0, 60, 35, key="n")

        price, gross, net = affordable_price(net_monthly, monthly_expenses, deposit_pct, rate, term, lti, tax_rate)

        st.success(f"💡 Maximum Affordable House Price: **£{price:,.0f}**")
        st.write(f"- Est. Gross Annual Salary: £{gross:,.0f}")
        st.write(f"- Net Annual Salary: £{net:,.0f}")

# --- CAR ---
with tab2:
    st.header("🚗 Car Calculator")
    subtab1, subtab2 = st.tabs(["📈 Salary Projection", "💰 Affordability"])

    with subtab1:
        st.subheader("How much salary do I need for this car?")
        price = st.number_input("Car price (£)", value=30000, step=1000, key="o")
        deposit_pct = st.slider("Deposit (%)", 0, 50, 10, key="p")
        rate = st.number_input("Loan interest rate (%)", value=7.0, step=0.1, key="q")
        term = st.slider("Loan term (years)", 1, 7, 5, key="r")
        lti = st.number_input("Loan-to-Income multiple", value=2.0, step=0.1, key="s")
        monthly_expenses = st.number_input("Monthly expenses (£)", value=1000, step=100, key="t")
        tax_rate = st.slider("Effective tax rate (%)", 0, 60, 35, key="u")

        deposit = price * deposit_pct / 100
        loan = price - deposit
        pay = monthly_payment(loan, rate, term)

        gross_lti, gross_afford, gross_needed = required_salary(loan, pay, monthly_expenses, lti, tax_rate)

        st.success(f"💡 Required Gross Annual Salary: **£{gross_needed:,.0f}**")
        st.write(f"- By Loan-to-Income: £{gross_lti:,.0f}") 
        st.write(f"- By Affordability: £{gross_afford:,.0f}")
        st.write(f"Monthly payment ≈ £{pay:,.0f}")

    with subtab2:
        st.subheader("How much car can I afford?")
        net_monthly = st.number_input("Net monthly salary (£)", value=2500, step=100, key="v")
        monthly_expenses = st.number_input("Monthly expenses (£)", value=1000, step=100, key="w")
        deposit_pct = st.slider("Deposit (%)", 0, 50, 10, key="x")
        rate = st.number_input("Loan interest rate (%)", value=7.0, step=0.1, key="y")
        term = st.slider("Loan term (years)", 1, 7, 5, key="z")
        lti = st.number_input("Loan-to-Income multiple", value=2.0, step=0.1, key="aa")
        tax_rate = st.slider("Effective tax rate (%)", 0, 60, 35, key="bb")

        price, gross, net = affordable_price(net_monthly, monthly_expenses, deposit_pct, rate, term, lti, tax_rate)

        st.success(f"💡 Maximum Affordable Car Price: **£{price:,.0f}**")
        st.write(f"- Est. Gross Annual Salary: £{gross:,.0f}")
        st.write(f"- Net Annual Salary: £{net:,.0f}")

# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Personal Finance Projection - UK", layout="wide")

# -------------------------
# Utility: UK TAX + NIC (2025/26)
# Sources: gov.uk income tax & rates/thresholds, gov.uk SDLT pages (see assistant citations)
# -------------------------
PERSONAL_ALLOWANCE = 12570  # 2025/26
# Income tax bands (2025/26): basic 20% up to 50,270, higher 40% up to 125,140, additional 45% above.
TAX_BANDS = [
    (0, 12570, 0.0),
    (12570, 50270, 0.20),
    (50270, 125140, 0.40),
    (125140, float("inf"), 0.45),
]

# NIC (Class 1 employee) simplified:
# Primary threshold: £12,570 per year (no NIC below). 12% between PT and Upper Earnings Limit (UEL).
# 2% above UEL. Historically UEL aligned with higher rate threshold ~50,270.
NIC_PT = 12570
NIC_UEL = 50270
NIC_RATES = [(NIC_PT, NIC_UEL, 0.12), (NIC_UEL, float("inf"), 0.02)]

def compute_income_tax(gross):
    """Return income tax for annual gross (GBP)."""
    tax = 0.0
    for low, high, rate in TAX_BANDS:
        if gross <= low:
            break
        taxable = min(gross, high) - low
        tax += taxable * rate
        if gross <= high:
            break
    return max(0.0, tax)

def compute_nic(gross):
    """Compute employee NIC (Class 1) for gross annual salary."""
    nic = 0.0
    for low, high, rate in NIC_RATES:
        if gross <= low:
            continue
        taxable = min(gross, high) - low
        nic += taxable * rate
    return max(0.0, nic)

def gross_to_net(gross):
    """Return (net_annual, tax, nic) for gross annual salary."""
    tax = compute_income_tax(gross)
    nic = compute_nic(gross)
    net = gross - tax - nic
    return net, tax, nic

def net_to_gross(target_net, guess_low=0.0, guess_high=1_000_000.0):
    """
    Estimate gross that yields approx target_net by binary search.
    Returns estimated gross, and (net, tax, nic) at that gross.
    """
    low = guess_low
    high = guess_high
    for _ in range(60):
        mid = (low + high) / 2.0
        net, _, _ = gross_to_net(mid)
        if net < target_net:
            low = mid
        else:
            high = mid
    gross = (low + high) / 2.0
    net, tax, nic = gross_to_net(gross)
    return gross, net, tax, nic

# -------------------------
# SDLT (Stamp Duty) for residential properties (slabbed)
# New zero band: £0-125,000 @0% (from April 2025). Then 2% up to 250k, 5% up to 925k, 10% up to 1.5m, 12% above.
SDLT_BANDS = [
    (0, 125000, 0.00),
    (125000, 250000, 0.02),
    (250000, 925000, 0.05),
    (925000, 1500000, 0.10),
    (1500000, float("inf"), 0.12),
]

def compute_sdlt(price):
    tax = 0.0
    for low, high, rate in SDLT_BANDS:
        if price <= low:
            break
        taxable = min(price, high) - low
        tax += taxable * rate
        if price <= high:
            break
    return tax

# -------------------------
# Loan math
# -------------------------
def monthly_payment(principal, annual_rate_percent, years):
    if principal <= 0 or years <= 0:
        return 0.0
    r = annual_rate_percent / 100.0 / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

# -------------------------
# Session: scenarios
# -------------------------
if "scenarios" not in st.session_state:
    st.session_state.scenarios = []  # list of dicts

def save_scenario(s):
    st.session_state.scenarios.append(s)

# -------------------------
# UI Layout
# -------------------------
st.title("🏠🚗 Personal Finance Projection — UK (2025/26 rules)")
st.caption("Choose mode and calculation type. Uses UK PAYE & NIC rules (tax year 2025/26) and SDLT slab rates (Apr 2025). Estimates only — see sources below.")

mode = st.radio("Select calculator", ["House", "Car"], horizontal=True)

calc_type = st.radio("Calculation type", ["Salary Projection", "Affordability"], horizontal=True,
                     help="Salary Projection: 'Given a price, what gross salary do I need?'\nAffordability: 'Given my salary and expenses, what price can I afford?'")

# Two-column main area: inputs left, outputs right
col_in, col_out = st.columns([1, 1.2], gap="large")

with col_in:
    st.markdown("### Inputs")
    # Common inputs
    price = st.number_input("Target price (£)", min_value=0, value=300_000, step=1000,
                            help="Target house/car price used in Salary Projection. In Affordability you'll see max price calculated.")
    deposit_pct = st.slider("Deposit (%)", 0, 50, 15,
                            help="Percent of price you'll put down as deposit. You may also set a deposit amount below to override.")
    deposit_amt = st.number_input("Deposit amount (£) — overrides % if >0", min_value=0, value=0, step=500,
                                 help="Enter explicit deposit amount to override percent.")
    term_years = st.slider("Term (years)", 1, 40, 25,
                           help="Length of mortgage/loan in years.")
    interest_rate = st.number_input("Interest rate (annual %)", min_value=0.0, value=5.0, step=0.1,
                                    help="Annual APR used to calculate monthly payments.")
    arrangement_fee = st.number_input("Arrangement / One-off fees (£)", min_value=0, value=1_500, step=50,
                                      help="One-off fees such as arrangement/solicitor/conveyancing (for house) or admin (car).")
    monthly_overheads = st.number_input("Monthly overheads (£)", min_value=0, value=500, step=50,
                                       help="Regular fixed outgoings (utilities, subscriptions).")
    monthly_expenses = st.number_input("Other monthly expenses (£)", min_value=0, value=1000, step=50,
                                       help="Food, transport, childcare, discretionary spend.")
    lti = st.number_input("Loan-to-Income multiple (LTI)", min_value=1.0, max_value=10.0, value=4.5, step=0.1,
                          help="Typical lender multiple of gross annual income used for eligibility checks.")
    # Affordability mode: primary user input is net monthly salary (take-home)
    net_monthly_salary = st.number_input("Net monthly salary (£) — take-home (Affordability)", min_value=0, value=3000, step=100,
                                        help="Enter take-home pay to compute how much you can afford. For Salary Projection you can leave this as-is.")
    effective_tax_rate = st.slider("Quick effective tax rate (%) used for simple estimates (alternative to PAYE calc)", 0, 50, 35,
                                   help="If you prefer not to use the detailed PAYE/NIC calc, this slider gives a simple gross/net conversion. Leave as-is to use the accurate UK PAYE+NIC calculator.")

    with st.expander("Advanced / UK-specific (Stamp Duty, stress test & insurance)"):
        show_sdlt = st.checkbox("Include Stamp Duty (SDLT) calc (House only)", value=True)
        stress_rate_shift = st.number_input("Stress test: increase interest rate by (+%)", value=2.0, step=0.1,
                                           help="Apply an increase to interest rate to evaluate affordability under stress (e.g., +2%).")
        maintenance_pct = st.number_input("Maintenance (% of property per year)", min_value=0.0, max_value=5.0, value=1.0, step=0.1,
                                         help="Estimated annual maintenance cost as % of property value.")
        insurance_monthly = st.number_input("Estimated insurance / car tax monthly (£)", min_value=0, value=50, step=10)

# -------------------------
# Calculations
# -------------------------
# Derived deposit
deposit = deposit_amt if deposit_amt > 0 else price * deposit_pct / 100.0
loan_amount = max(0.0, price - deposit)

# Monthly payment (base)
monthly_pay = monthly_payment(loan_amount, interest_rate, term_years)
monthly_pay_stress = monthly_payment(loan_amount, interest_rate + stress_rate_shift, term_years)

# SDLT if house
sdlt = compute_sdlt(price) if (mode == "House" and show_sdlt) else 0.0

# Maintenance estimate
annual_maintenance = price * (maintenance_pct / 100.0)
monthly_maintenance = annual_maintenance / 12.0

# PAYE/NIC and gross/net conversions
# We'll compute both: accurate (UK PAYE+NIC) and simple effective-tax method.
gross_from_net_simple = None
if effective_tax_rate > 0 and effective_tax_rate < 100:
    gross_from_net_simple = (net_monthly_salary * 12.0) / (1.0 - effective_tax_rate / 100.0)
else:
    gross_from_net_simple = net_monthly_salary * 12.0

# accurate PAYE approach: binary search net_to_gross helper
def required_gross_for_affordability(net_monthly_required):
    """Given required net monthly, return gross est using full PAYE+NIC calc."""
    target_net_annual = net_monthly_required * 12.0
    gross, net, tax, nic = net_to_gross(target_net_annual, guess_high=2_000_000)
    return gross, net, tax, nic

# Salary Projection: given price & loan, compute required gross (two methods)
def salary_projection_methods():
    # 1) LTI method (simple): gross = loan_amount / lti
    gross_by_lti = loan_amount / lti if lti > 0 else 0.0

    # 2) Affordability method: required net monthly = monthly_pay + overheads + expenses + maintenance + insurance
    required_net_monthly = monthly_pay + monthly_overheads + monthly_expenses + monthly_maintenance + insurance_monthly
    # convert required net monthly to gross using PAYE/NIC accurate method
    gross_by_afford, net_calc, tax_calc, nic_calc = required_gross_for_affordability(required_net_monthly)
    # as fallback provide simple gross estimate
    gross_by_afford_simple = (required_net_monthly * 12.0) / (1.0 - effective_tax_rate / 100.0) if effective_tax_rate < 100 else 0.0

    return {
        "gross_by_lti": gross_by_lti,
        "gross_by_afford": gross_by_afford,
        "gross_by_afford_simple": gross_by_afford_simple,
        "required_net_monthly": required_net_monthly,
        "tax_calc": tax_calc,
        "nic_calc": nic_calc,
    }

# Affordability Projection: given net salary & expenses compute max mortgage / price
def affordability_projection_methods():
    # Use accurate gross from net
    gross_annual, net_annual, tax_calc, nic_calc = net_to_gross(net_monthly_salary * 12.0, guess_high=2_000_000)[:4]
    # LTI cap
    mortgage_by_lti = gross_annual * lti
    # Affordability cap by payments: available for mortgage = net_monthly_salary - (overheads + expenses + maintenance + insurance)
    available_for_mortgage_monthly = max(0.0, net_monthly_salary - (monthly_overheads + monthly_expenses + monthly_maintenance + insurance_monthly))
    # Convert monthly available into a maximum loan by inverting monthly payment formula:
    # approximate maximum loan if monthly payment = available_for_mortgage_monthly
    r = interest_rate / 100.0 / 12.0
    n = term_years * 12
    if r == 0:
        mortgage_by_payment = available_for_mortgage_monthly * n
    else:
        # principal = payment * (1 - (1+r)^-n) / r
        mortgage_by_payment = available_for_mortgage_monthly * (1 - (1 + r) ** (-n)) / r
    # Conservative mortgage is min of LTI and payment-based
    mortgage_affordable = min(mortgage_by_lti, mortgage_by_payment)
    # Price = mortgage / (1 - deposit_pct) (if deposit_pct==100 => price == deposit)
    # To avoid division by 0:
    denom = (1 - deposit_pct / 100.0) if deposit_amt == 0 else (loan_amount / price if price > 0 else 0.0)
    # If user provided explicit deposit amount, compute price from mortgage + deposit:
    if deposit_amt > 0:
        price_affordable = mortgage_affordable + deposit_amt
    else:
        # deposit % path
        if denom <= 0:
            price_affordable = mortgage_affordable  # fallback
        else:
            price_affordable = mortgage_affordable / (1 - deposit_pct / 100.0)
    return {
        "gross_annual": gross_annual,
        "net_annual": net_annual,
        "mortgage_by_lti": mortgage_by_lti,
        "mortgage_by_payment": mortgage_by_payment,
        "mortgage_affordable": mortgage_affordable,
        "price_affordable": price_affordable,
        "available_for_mortgage_monthly": available_for_mortgage_monthly,
        "tax_calc": tax_calc,
        "nic_calc": nic_calc,
    }

# -------------------------
# Display outputs
# -------------------------
with col_out:
    st.markdown("### Results & Charts")
    if calc_type == "Salary Projection":
        sp = salary_projection_methods()
        gross_needed = max(sp["gross_by_lti"], sp["gross_by_afford"])
        st.metric("Required Gross Annual Salary (conservative)", f"£{gross_needed:,.0f}")
        st.write("**Breakdown**")
        st.write(f"- By Loan-to-Income (LTI): £{sp['gross_by_lti']:,.0f}")
        st.write(f"- By Affordability (PAYE+NIC accurate): £{sp['gross_by_afford']:,.0f}")
        st.write(f"- Required net monthly to cover loan + costs: £{sp['required_net_monthly']:,.0f}")
        st.write(f"- Estimated monthly mortgage payment: £{monthly_pay:,.0f} (stress: £{monthly_pay_stress:,.0f})")
        if sdlt > 0:
            st.write(f"- Stamp Duty (SDLT) estimate: £{sdlt:,.0f}")
        st.write(f"- Annual maintenance estimate: £{annual_maintenance:,.0f} ({maintenance_pct}% pa)")
        # charts: pie of net monthly distribution assuming net from gross_needed
        gross_est = gross_needed
        net_est, tax_est, nic_est = gross_to_net(gross_est)
        disposable = net_est/12.0 - (monthly_pay + monthly_overheads + monthly_expenses + monthly_maintenance + insurance_monthly)
        labels = ["Mortgage payment", "Overheads + expenses", "Maintenance + insurance", "Disposable"]
        values = [monthly_pay, monthly_overheads + monthly_expenses, monthly_maintenance + insurance_monthly, max(0.0, disposable)]
        fig, ax = plt.subplots(figsize=(4,3))
        ax.pie(values, labels=labels, autopct=lambda p: f"{p:.0f}%\n(£{int(p/100*sum(values)):,.0f})", startangle=140)
        ax.set_title("Monthly net distribution (est)")
        st.pyplot(fig)

        # Save scenario
        if st.button("Save scenario (Salary Projection)"):
            save_scenario({
                "mode": mode,
                "type": calc_type,
                "price": price,
                "deposit_pct": deposit_pct,
                "deposit_amt": deposit_amt,
                "term_years": term_years,
                "interest_rate": interest_rate,
                "monthly_pay": monthly_pay,
                "gross_needed": gross_needed,
                "sdlt": sdlt,
            })
            st.success("Scenario saved.")

    else:  # Affordability
        ap = affordability_projection_methods()
        st.metric("Maximum Affordable Price (conservative)", f"£{ap['price_affordable']:,.0f}")
        st.write("**Breakdown**")
        st.write(f"- Max mortgage by LTI: £{ap['mortgage_by_lti']:,.0f}")
        st.write(f"- Max mortgage by payment capacity: £{ap['mortgage_by_payment']:,.0f}")
        st.write(f"- Available for mortgage (per month): £{ap['available_for_mortgage_monthly']:,.0f}")
        st.write(f"- If you buy at price above, SDLT (if applicable) may apply")

        # Show monthly payment at that mortgage
        monthly_for_affordable_loan = monthly_payment(ap["mortgage_affordable"], interest_rate, term_years)
        st.write(f"- Estimated monthly payment at that mortgage: £{monthly_for_affordable_loan:,.0f}")

        # Pie chart showing net allocation
        gross_est = ap["gross_annual"]
        net_est = ap["net_annual"]
        mortgage_monthly = monthly_for_affordable_loan
        disposable = net_est/12.0 - (mortgage_monthly + monthly_overheads + monthly_expenses + monthly_maintenance + insurance_monthly)
        labels = ["Mortgage", "Overheads+Expenses", "Maintenance+Insurance", "Disposable"]
        values = [mortgage_monthly, monthly_overheads + monthly_expenses, monthly_maintenance + insurance_monthly, max(0.0, disposable)]
        fig, ax = plt.subplots(figsize=(4,3))
        ax.pie(values, labels=labels, autopct=lambda p: f"{p:.0f}%\n(£{int(p/100*sum(values)):,.0f})", startangle=140)
        ax.set_title("Monthly net distribution (your inputs)")
        st.pyplot(fig)

        if st.button("Save scenario (Affordability)"):
            save_scenario({
                "mode": mode,
                "type": calc_type,
                "net_monthly_salary": net_monthly_salary,
                "deposit_pct": deposit_pct,
                "deposit_amt": deposit_amt,
                "term_years": term_years,
                "interest_rate": interest_rate,
                "price_affordable": ap["price_affordable"],
                "mortgage_affordable": ap["mortgage_affordable"],
            })
            st.success("Scenario saved.")

# -------------------------
# Scenario comparison area
# -------------------------
st.markdown("---")
st.header("Saved Scenarios & Comparison")
if len(st.session_state.scenarios) == 0:
    st.info("No scenarios saved yet. Use 'Save scenario' to add one and compare multiple scenarios.")
else:
    df = pd.DataFrame(st.session_state.scenarios)
    # Normalize columns for display
    st.dataframe(df.fillna(""), width=1100)
    # Allow selection of scenarios to compare
    selected = st.multiselect("Select scenarios to compare (by row index)", options=list(range(len(df))), format_func=lambda i: f"{i}: {df.loc[i].get('type','')} - {df.loc[i].get('mode','')} - £{int(df.loc[i].get('price', df.loc[i].get('price_affordable',0))):,}")
    if selected:
        compare_df = df.loc[selected].copy()
        st.markdown("### Comparison chart: Price / Gross Needed / Monthly Payment")
        fig2, ax2 = plt.subplots(figsize=(8,4))
        # try to plot price and gross_needed/mortgage values
        x = [f"{i}" for i in selected]
        prices = []
        gross_needed = []
        monthlys = []
        for i in selected:
            row = df.loc[i]
            prices.append(row.get("price", row.get("price_affordable", 0)))
            gross_needed.append(row.get("gross_needed", row.get("gross_annual", 0)))
            monthlys.append(row.get("monthly_pay", row.get("mortgage_affordable", 0)) )
        ax2.bar([p + "\nprice" for p in x], prices, label="Price")
        ax2.bar([p + "\ngross" for p in x], gross_needed, label="Gross needed")
        ax2.set_ylabel("GBP")
        ax2.legend()
        st.pyplot(fig2)

# -------------------------
# Footer & Sources
# -------------------------
st.markdown("---")
st.caption("**Notes & sources:** This tool uses UK Income Tax bands and NIC rules for 2025/26 (Personal Allowance £12,570; basic 20% up to £50,270; higher 40% up to £125,140; additional 45% above). Employee NIC: primary threshold £12,570; 12% between threshold and upper earnings limit (~£50,270), 2% above. SDLT (Stamp Duty) slabbed rates used for residential properties (0% up to £125k, 2% next band, etc.). These are estimates for guidance only; always check with lenders/official calculators.")
st.write("If you'd like, I can: (1) add a downloadable PDF report, (2) make the PAYE/NIC toggles explicit (detailed vs simple), (3) add sensitivity sliders to show affordable price vs interest rate graph. Which would you like next?")

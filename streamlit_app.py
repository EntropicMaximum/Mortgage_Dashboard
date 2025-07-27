import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def calculate_monthly_payment(principal, annual_interest_rate, years):
    monthly_rate = annual_interest_rate / 12
    n_payments = years * 12
    return monthly_rate * principal / (1 - (1 + monthly_rate) ** -n_payments)

def amortization_schedule(principal, annual_interest_rate, years):
    monthly_rate = annual_interest_rate / 12
    n_payments = years * 12
    payment = calculate_monthly_payment(principal, annual_interest_rate, years)
    balances, interests, principals, payments = [], [], [], []
    balance = principal
    for month in range(1, n_payments + 1):
        interest = balance * monthly_rate
        principal_payment = payment - interest
        if principal_payment > balance:
            principal_payment = balance
            payment_this_month = interest + principal_payment
        else:
            payment_this_month = payment
        balance -= principal_payment
        balances.append(balance)
        interests.append(interest)
        principals.append(principal_payment)
        payments.append(payment_this_month)
        if balance <= 0:
            break
    df = pd.DataFrame({
        'Month': range(1, len(balances) + 1),
        'Balance': balances,
        'Interest': interests,
        'Principal': principals,
        'Payment': payments
    })
    df['Cumulative Interest'] = df['Interest'].cumsum()
    df['Cumulative Payment'] = df['Payment'].cumsum()
    return df

def amortization_schedule_with_payoffs(principal, annual_interest_rate, years,
                                       monthly_extra_payment=0.0,
                                       lump_sum_month=None,
                                       lump_sum_amount=0.0):
    monthly_rate = annual_interest_rate / 12
    n_payments = years * 12
    base_payment = calculate_monthly_payment(principal, annual_interest_rate, years)
    balances, interests, sched_princs, extras, payments = [], [], [], [], []
    balance = principal
    for month in range(1, n_payments + 1):
        interest = balance * monthly_rate
        sched_principal = base_payment - interest
        extra = monthly_extra_payment
        if lump_sum_month and month == lump_sum_month:
            extra += lump_sum_amount
        total_principal = sched_principal + extra
        if total_principal > balance:
            total_principal = balance
            sched_principal = min(sched_principal, total_principal)
            extra = total_principal - sched_principal
        payment_this_month = interest + total_principal
        balance -= total_principal
        balances.append(balance)
        interests.append(interest)
        sched_princs.append(sched_principal)
        extras.append(extra)
        payments.append(payment_this_month)
        if balance <= 0:
            break
    df = pd.DataFrame({
        'Month': range(1, len(balances) + 1),
        'Balance': balances,
        'Interest': interests,
        'Scheduled Principal': sched_princs,
        'Extra Principal': extras,
        'Payment': payments
    })
    df['Cumulative Interest'] = df['Interest'].cumsum()
    df['Cumulative Payment'] = df['Payment'].cumsum()
    return df

def amortization_refinance(principal, annual_interest_rate, years,
                           monthly_payment, start_month,
                           cum_interest_offset, cum_payment_offset):
    monthly_rate = annual_interest_rate / 12
    n_payments = int(years * 12)
    months, balances, interests, payments = [], [], [], []
    cumul_ints, cumul_pays = [], []
    balance = principal
    cum_int = cum_interest_offset
    cum_pay = cum_payment_offset
    for m in range(1, n_payments + 1):
        interest = balance * monthly_rate
        princ = monthly_payment - interest
        if princ > balance:
            princ = balance
            payment_m = interest + princ
        else:
            payment_m = monthly_payment
        balance -= princ
        cum_int += interest
        cum_pay += payment_m
        months.append(start_month + m)
        balances.append(balance)
        interests.append(interest)
        payments.append(payment_m)
        cumul_ints.append(cum_int)
        cumul_pays.append(cum_pay)
        if balance <= 0:
            break
    return pd.DataFrame({
        'Month': months,
        'Balance': balances,
        'Interest': interests,
        'Payment': payments,
        'Cumulative Interest': cumul_ints,
        'Cumulative Payment': cumul_pays
    })

def main():
    st.title("Mortgage Plan Interactive")

    principal = st.slider("Principal", 100_000.0, 1_000_000.0, 580_000.0, step=10_000.0)
    rate_before = st.slider("Annual Rate Before Refi", 0.035, 0.055, 0.0427,
                            step=0.0001, format="%.4f")
    rate_after = st.slider("Annual Rate After Refi", 0.035, 0.055, 0.0477,
                           step=0.0001, format="%.4f")
    years = st.slider("Loan Duration (years)", 1, 30, 24)
    extra_before = st.slider("Monthly Extra Before Refi", 0, 2_000, 500, step=100)
    extra_after = st.slider("Monthly Extra After Refi", 0, 2_000, 1_000, step=100)
    lump_month = st.slider("Lump Sum Month", 0, years * 12, 1)
    lump_amount = st.slider("Lump Sum Amount", 0.0, 500_000.0, 300_000.0,
                            step=5_000.0)

    orig_payment = calculate_monthly_payment(principal, rate_before, years)
    st.write(f"**Original Monthly Payment:** ${orig_payment:,.2f}")

    baseline = amortization_schedule(principal, rate_before, years)
    pre_refi = amortization_schedule_with_payoffs(principal, rate_before, years,
                                                  extra_before, lump_month, lump_amount)

    if lump_month <= len(pre_refi):
        pre = pre_refi.iloc[lump_month - 1]
    else:
        pre = pre_refi.iloc[-1]
    bal_post = pre.Balance
    cum_int_pre = pre["Cumulative Interest"]
    cum_pay_pre = pre["Cumulative Payment"]
    rem_years = years - lump_month / 12

    new_std = calculate_monthly_payment(bal_post, rate_after, rem_years)
    new_std_plus = new_std + extra_after
    st.write(f"**Refi Standard Payment:** ${new_std:,.2f}")
    st.write(f"**Refi + Extra Payment:** ${new_std_plus:,.2f}")

    refi_std = amortization_refinance(bal_post, rate_after, rem_years,
                                      new_std, lump_month, cum_int_pre, cum_pay_pre)
    refi_extra = amortization_refinance(bal_post, rate_after, rem_years,
                                        new_std_plus, lump_month, cum_int_pre, cum_pay_pre)

    def plot_series(df_dict, col, title):
        fig, ax = plt.subplots()
        for name, df in df_dict.items():
            ax.plot(df.Month / 12, df[col], label=name)
        ax.set_title(title)
        ax.set_xlabel("Years")
        ax.set_ylabel(col)
        ax.legend()
        st.pyplot(fig)

    dfs = {
        "Original": baseline,
        "Pre-refi w/ extras": pre_refi,
        "Post-refi std": refi_std,
        "Post-refi + extra": refi_extra
    }
    plot_series(dfs, "Balance", "Remaining Loan Balance")
    plot_series(dfs, "Cumulative Interest", "Cumulative Interest Paid")
    plot_series(dfs, "Cumulative Payment", "Cumulative Payments")

if __name__ == "__main__":
    main()

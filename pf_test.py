from matplotlib import pyplot as plt
import personalfinance as pf
import numpy as np
import pandas as pd

# User Input
annual_salary = 100000
age = 28
filing = 1
necessity_pct = 0.60
years_worked = 5
years_to_retirement = 35
years_to_live = 25 # Post-retirement
health_ins = 0
loans = 0
freq = 26
savings_rate = 0.5

# Model Set Up
b = pf.Budget(annual_salary, years_worked, years_to_retirement, years_to_live, necessity_pct, freq, health_ins, loans)
t = pf.Tools()
v = pf.Visualization()
r = b.BudgetRecommendation(annual_salary)
n = b.NetWorth(r[6], r[7], r[8], r[9] * savings_rate)
n_adj = t.InflationAdj(n, years_to_retirement, b.inflation)
m = b.RetirementIncome(n[1], n[2], n[4])
m_adj = t.InflationAdj(m, years_to_retirement, b.inflation)

# Convert output to USD
rc = t.Convert(r)
nc = t.Convert(n)
nc_adj = t.Convert(n_adj)
mc = t.Convert(m)
mc_adj = t.Convert(m_adj)

# JY's budget recommendation
print('Biweekly Budget Recommendation'
      '\n',
      '\nGross Paycheck: ', rc[0], 
      '\nFederal Tax: ', rc[1], 
      '\nSS Tax: ', rc[2],
      '\nMCR Tax: ', rc[3],
      '\nState Tax: ', rc[4],
      '\nMax Rent: ', rc[5],
      '\n401k: ', rc[6],
      '\nROTH IRA: ', rc[7],
      '\nHSA: ', rc[8],
      '\nRemaining (Savings/Leisure/Ins): ', rc[9],
      '\n')

# JY's max rent/car recommendation
print('Max Monthly Rent: ', rc[10],
      '\nMax Car Value: ', rc[11],
      '\n')

# Forecast of retirement savings
print('Future Value of Retirement Vehicles & Other Savings in', years_to_retirement, 'Years',
      '\n',
      '\n401k: ', nc[1],
      '\nROTH IRA: ', nc[2],
      '\nHSA: ', nc[3],
      '\nOther: ', nc[4],
      '\nTotal: ', nc[0],
      '\n')
'''
# Estimate of after-tax monthly retirement income
print('Monthly After-Tax Income Assuming', ytl, 'Years to Live (Excluding HSA)',
      '\n',
      '\nGross Monthly Income: ', mc[0],
      '\nMonthly Taxes: ', mc[1],
      '\nNet Monthly Income: ', mc[2],
      '\n')
'''
# Estimate of after-tax monthly retirement income inflation adjusted
print('Monthly After-Tax Retirement Income Assuming', years_to_live, 'Years to Live (Excluding HSA)',
      '\nNote: Following numbers are inflation adjusted to present day dollars from the year you retire',
      '\n',
      '\nGross Monthly Retirement Income: ', mc_adj[0],
      '\nMonthly Taxes: ', mc_adj[1],
      '\nNet Monthly Retirement Income: ', mc_adj[2])

# Visualization

f = b.Forecast()
v.BarChart(f)

# Pie Chart
categories = ['Federal Tax', 'State Tax', 'Max Rent', '401k', 'ROTH IRA', 'HSA', 'Remaining']
variables = r[1:]

# Colors
colors = ['#ED9A88', '#F0C3A2', '#A2C3F0', '#E5CCFF', '#8DF7C8', '#8DF3F7', '#E5F78D']

# Explode
explode = (0, 0, 0, 0, 0, 0, 0)

fig1, ax1 = plt.subplots()
ax1.pie(variables, explode = explode, colors = colors, labels = categories, autopct = '%1.1f%%', shadow = True, startangle = 90)

# Draw circle
center_circle = plt.Circle((0,0), 0.80, fc='white')
fig = plt.gcf()
fig.gca().add_artist(center_circle)

# Equal aspect ratio ensures that pie is drawn as a circle
ax1.axis('equal')
plt.tight_layout()
plt.show()

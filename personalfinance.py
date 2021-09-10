import numpy as np
import matplotlib as plt
import pandas as pd
import locale
import matplotlib.pyplot as plt
import matplotlib.ticker as tick
from operator import itemgetter

class Budget():

    def __init__(self, salary, years_worked, years_to_retirement, years_to_live, necessity_pct, freq=26, health_ins=0, current_loans=0, 
                 current_401k=0, current_roth=0, current_hsa=0, current_other=0, s_return=0.07, b_return=0.02, stocks=0.9, bonds=0.1, inflation=0.02, 
                 salary_inc=0.02, savings_rate=0.50):

        self.salary = salary
        self.freq = freq
        self.health_ins = health_ins
        self.current_loans = current_loans
        self.current_401k = current_401k
        self.current_roth = current_roth
        self.current_hsa = current_hsa
        self.current_other = current_other
        self.necessity_pct = necessity_pct
        self.annual_s_return = s_return
        self.annual_b_return = b_return
        self.stocks = stocks
        self.bonds = bonds
        self.annual_blended_return = s_return * stocks + b_return * bonds
        self.inflation = inflation
        self.salary_inc = salary_inc
        self.savings_rate = savings_rate
        self.years_worked = years_worked
        self.years_to_retirement = years_to_retirement
        self.years_to_live = years_to_live
    
    # Estimate returns of 401k, ROTH IRA, HSA, and other investments based on biweekly contributions
    def NetWorth(self, r_401k, r_roth, r_hsa, other, current_401k=0, current_roth=0, current_hsa=0, current_other=0):

        r = (1 + self.annual_blended_return) ** (1 / self.freq) - 1
        n = self.years_to_retirement * self.freq # N biweekly periods

        fv_401k = round(Tools.FVA(self, r_401k, n, r), 2)
        fv_roth_ira = round(Tools.FVA(self, r_roth, n, r), 2)
        fv_hsa = round(Tools.FVA(self, r_hsa, n, r), 2)
        fv_other = round(Tools.FVA(self, other, n, r), 2)
        total = fv_401k + fv_roth_ira + fv_hsa + fv_other
        return total, fv_401k, fv_roth_ira, fv_hsa, fv_other

    # Forecast value of each vehicle year by year
    def Forecast(self):
        years = {}

        # Initialize starting point
        current_salary = self.salary
        current_other = self.current_other
        current_401k = self.current_401k
        current_roth = self.current_roth
        current_hsa = self.current_hsa
        #current_loans = self.current_loans
        years[0] = (current_other, current_401k, current_roth, current_hsa)

        for i in range(1, self.years_to_retirement):

            # Based on year i, compute budget recommendations that determine levels of investment, savings, loan payoffs
            budget = self.BudgetRecommendation(current_salary)
            rate = (1 + self.annual_blended_return) ** (1 / self.freq) - 1
            invest_401k = budget[6]
            invest_roth = budget[7]
            invest_hsa = budget[8]
            invest_other = budget[9] * self.savings_rate

            # Compute end of year value as sum of future value of annuity investments and current investments forwarded by one year
            current_401k = current_401k * (1 + self.annual_blended_return) + Tools.FVA(self, invest_401k, self.freq, rate)
            current_roth = current_roth * (1 + self.annual_blended_return) + Tools.FVA(self, invest_roth, self.freq, rate)
            current_hsa = current_hsa * (1 + self.annual_blended_return) + Tools.FVA(self, invest_hsa, self.freq, rate)
            current_other = current_other * (1 + self.annual_blended_return) + Tools.FVA(self, invest_other, self.freq, rate)

            # Store values in dict and forward salary by one year
            years[i] = (current_other, current_401k, current_roth, current_hsa)
            current_salary = current_salary * (1 + self.salary_inc)

        # Return dictionary representing each year's net value (general savings, 401k, ROTH IRA, HSA, loans, etc.)
        return years

    # Estimate monthly income in retirement based on 401k and ROTH IRA based on number of years to live based on TODAY's tax rate
    def RetirementIncome(self, fv_401k, fv_roth_ira, fv_other, stocks=0.1, bonds=0.9):
        
        r = (1 + self.annual_blended_return) ** (1 / 12) - 1
        n = self.years_to_live * 12

        # Gross Monthly Payouts
        gross_401k = Tools.AP(self, fv_401k, n, r)
        gross_roth_ira = Tools.AP(self, fv_roth_ira, n, r)
        gross_other = Tools.AP(self, fv_other, n, r)
        gross_taxable_monthly = gross_401k + gross_other
        gross_taxable_annual = gross_taxable_monthly * 12

        f_tax = self.FederalIncomeTax(gross_taxable_annual) * self.freq # Convert back to annual
        s_tax = self.StateIncomeTax(gross_taxable_annual) * self.freq # Convert back to annual

        gross_monthly = gross_401k + gross_roth_ira + gross_other
        monthly_taxes = (f_tax + s_tax) / 12
        net_monthly = gross_401k + gross_roth_ira + gross_other - (f_tax + s_tax) / 12
        return gross_monthly, monthly_taxes, net_monthly

    # Budget determines the optimal breakdown of your budget
    def BudgetRecommendation(self, salary, hsa=True):

        gross_pay = salary / self.freq
        retirement = self.Retirement(self.necessity_pct)
        annual_taxable = salary * (1 - (retirement[0] + retirement[2]))
        f_tax = self.FederalIncomeTax(annual_taxable)
        ss_tax = self.SSMCRTax(annual_taxable)[0]
        mcr_tax = self.SSMCRTax(annual_taxable)[1]
        s_tax = self.StateIncomeTax(annual_taxable)

        net_pay = gross_pay - f_tax - ss_tax - mcr_tax - s_tax
        r_401k = gross_pay * retirement[0]
        r_roth_ira = gross_pay * retirement[1]
        r_hsa = gross_pay * retirement[2]
        rent = gross_pay * self.RentMax()
        leisure = net_pay - r_401k - r_roth_ira - r_hsa - rent

        # Recommends maximum monthly rent (~30% adjusted of after-tax pay) and total car value (~35% of annual income)
        max_rent = rent * self.freq / 12
        max_car = salary * 0.35

        return gross_pay, f_tax, ss_tax, mcr_tax, s_tax, rent, r_401k, r_roth_ira, r_hsa, leisure, max_rent, max_car

    # Returns bi-weekly federal income tax
    def FederalIncomeTax(self, annual_taxable_salary, filing=1):

        # Filing (Key) 1 - Single, 2 - Head of Household, 3 - Married Filing Jointly/Qualifying Widow, 4 - Married Filing Separately
        df = pd.read_excel(r'C:\Users\David Jaeyun Kim\Desktop\Administrative\Coding\Personal Finance\fed_income_tax_2021.xlsx')
        filing_dict = {1: ('Single_Min','Single_Max'), 2: ('MFJ_Min','MFJ_Max'), 3: ('HOH_Min','HOH_Max')}
        df = df[['Rate', filing_dict[filing][0], filing_dict[filing][1]]]

        if annual_taxable_salary < 0 or annual_taxable_salary > 100000000000:
            print('Error: Enter a valid salary')
        else:
            for i in range(df.shape[0]):
                pct = float(df.iloc[i,0])
                min = float(df.iloc[i,1])
                max = float(df.iloc[i,2])
                if round(annual_taxable_salary, 0) > min and round(annual_taxable_salary, 0) < max:
                    tax = annual_taxable_salary * pct / self.freq
                    return tax
    
    # Returns Social Security and Medicare tax
    def SSMCRTax(self, annual_taxable_salary, filing=1):

        # Filing (Key) 1 - Single, 2 - Head of Household, 3 - Married Filing Jointly/Qualifying Widow, 4 - Married Filing Separately
        if filing == 1:

            # Compute 2021 Social Security Tax
            ss_tax_rate = 0.062
            ss_max = 142800

            if annual_taxable_salary > ss_max:
                ss_tax = ss_max * ss_tax_rate / self.freq
            else:
                ss_tax = annual_taxable_salary * ss_tax_rate / self.freq

            # Compute 2021 Medicare Tax
            mcr_tax_rate_1 = 0.0145
            mcr_tax_rate_2 = 0.0235
            mcr_breakpoint = 200000

            if annual_taxable_salary > mcr_breakpoint:
                mcr_tax = (mcr_breakpoint * mcr_tax_rate_1 + (annual_taxable_salary - mcr_breakpoint) * mcr_tax_rate_2) / self.freq
            else:
                mcr_tax = annual_taxable_salary * mcr_tax_rate_1 / self.freq
            
        return ss_tax, mcr_tax

    # Returns bi-weekly state income tax
    def StateIncomeTax(self, annual_taxable_salary, state = 'CA', filing = 1):

        # Filing (Key) 1 - Single, 2 - Head of Household, 3 - Married Filing Jointly/Qualifying Widow, 4 - Married Filing Separately
        if filing == 1:
            tax_single = np.array([[0.010, 0, 8809],
                                   [0.020, 8810, 20883],
                                   [0.040, 20884, 32960],
                                   [0.060, 32961, 45753],
                                   [0.080, 45754, 57824],
                                   [0.093, 57825, 295373],
                                   [0.103, 295374, 354445],
                                   [0.113, 354446, 590743],
                                   [0.123, 590742, 1000000],
                                   [0.133, 1000001, 100000000000]])
        
        if annual_taxable_salary < 0 or annual_taxable_salary > 100000000000:
            print('Error: Enter a valid salary')
        else:
            for bracket in tax_single:
                pct = bracket[0]
                min = bracket[1]
                max = bracket[2]
                if round(annual_taxable_salary, 0) > min and round(annual_taxable_salary, 0) < max:
                    tax = round(annual_taxable_salary * pct / self.freq, 2)
                    return tax

    # Determines Social Security Benefits (NOT COMPLETE)
    def SocialSecurity(self, salary):
        return

        # AIME Calculation
        AIME = Tools.AIME(self, salary, self.salary_inc, self.years_worked, self.years_to_retirement)

        # PIA Calculation
        
    # Recommends 401k percentage based on income
    def Retirement(self, necessity_pct, hsa=True):

        # Set up initial assumptions
        gross_pay = round(self.salary / self.freq, 2)
        f_tax = self.FederalIncomeTax(self.salary) + self.SSMCRTax(self.salary)[0] + self.SSMCRTax(self.salary)[1]
        s_tax = self.StateIncomeTax(self.salary)
        r_401k_limit = 19500
        r_roth_ira_limit = 6000
        r_hsa_limit = 3500
        rec_401k = [0.672, 0.765]
        rec_roth_ira = [0.207, 0.235]
        rec_hsa = [0.121, 0.000]
        roth_ira_earnings_limit = 140000

        net_pay = gross_pay - f_tax - s_tax
        remaining_pay = net_pay * (1 - necessity_pct)

        if net_pay * self.freq > roth_ira_earnings_limit:
            if hsa == True:
                if remaining_pay * self.freq >= r_401k_limit + r_hsa_limit:
                    pct_401k = r_401k_limit / self.salary
                    pct_hsa = r_hsa_limit / self.salary
                    return (pct_401k, 0, pct_hsa)
                else:
                    pct_401k = remaining_pay * rec_401k[0] / gross_pay
                    pct_hsa = remaining_pay * rec_hsa[0] / gross_pay
                    return (pct_401k, 0, pct_hsa)

            else:
                if remaining_pay >= r_401k_limit:
                    pct_401k = r_401k_limit / gross_pay
                    return (pct_401k, 0, 0)
                else:
                    pct_401k = remaining_pay * rec_401k[1] / gross_pay
                    return (pct_401k, 0, 0)
        
        else:
            if hsa == True:
                if remaining_pay * self.freq >= r_401k_limit + r_roth_ira_limit + r_hsa_limit:
                    pct_401k = r_401k_limit / self.salary
                    pct_roth_ira = r_roth_ira_limit / self.salary
                    pct_hsa = r_hsa_limit / self.salary
                    return (pct_401k, pct_roth_ira, pct_hsa)
                else:
                    pct_401k = remaining_pay * rec_401k[0] / gross_pay
                    pct_roth_ira = remaining_pay * rec_roth_ira[0] / gross_pay
                    pct_hsa = remaining_pay * rec_hsa[0] / gross_pay
                    return (pct_401k, pct_roth_ira, pct_hsa)

            else:
                if remaining_pay >= r_401k_limit + r_roth_ira_limit:
                    pct_401k = r_401k_limit / gross_pay
                    pct_roth_ira = r_roth_ira_limit / gross_pay
                    return (pct_401k, pct_roth_ira, 0)
                else:
                    pct_401k = remaining_pay * rec_401k[1] / gross_pay
                    pct_roth_ira = remaining_pay * rec_roth_ira[1] / gross_pay
                    return (pct_401k, pct_roth_ira, 0)

    # Recommends rent as a percentage of gross income
    def RentMax(self):

        # Start with $50k annual salary with a rent max of 30% of gross pay. Assume factor diminishes by 98% for each increase in $10k
        baseline_index = 5
        baseline_pct = 0.30
        dim_factor = 0.98
        salary_index = self.salary / 10000

        if salary_index <= baseline_index:
            return baseline_pct
        else:
            marginal = salary_index - baseline_index + 1
            rent_pct = baseline_pct * (dim_factor ** marginal)
            return rent_pct

class Tools():

    # Calculates future value based on biweekly payments | FV = C * ((1 + i) ** n - 1) / i
    def FVA(self, C, n, r):
        fv = C * ((1 + r) ** n - 1) / r
        return fv

    # Calculates present value based on biweekly payments | PV = C * (1 - (1 + i) ** (-n)) / i
    def PVA(self, C, n, r):
        #pv = self.FV(C, n, r) / (1 + r) ** n
        pv = C * (1 - (1 + r) ** (-n)) / r
        return pv

    # Calculates annuity payout, given principle amount | d = C * (r) / (1 - (1 + r) ** (-n))
    def AP(self, C, n, r):
        d = C * r / (1 - (1 + r) ** (-n))
        return d

    # Calculates estimate of past and future salary based on number of years worked and number of years to retirement
    def AIME(self, salary, salary_inc, years_worked, years_to_retirement):
        # Assume salary increases apply in both directions

        age_salary = {}
        total_years = years_worked + years_to_retirement

        # Estimate salary for years prior
        for i in range(years_worked):
            index = years_worked - i
            age_salary[index] = salary * (1 + salary_inc) ** (-i)
        
        # Estimate salary for years forward
        for i in range(years_to_retirement):
            index = years_worked + i
            age_salary[index] = salary * (1 + salary_inc) ** i

        # Sum the top 35 years of earnings and divide through by total number of months worked
        if total_years > 35:
            salary_sum = dict(sorted(age_salary.items(), key=itemgetter(1), reverse=True)[:35])
            AIME = sum(salary_sum.values()) / (35 * 12)
        else:
            salary_sum = dict(sorted(age_salary.items(), key=itemgetter(1), reverse=True)[:total_years])
            AIME = sum(salary_sum.values()) / (total_years * 12)
        return AIME

    # Converts all float items in a list to dollars
    def Convert(self, list):
        locale.setlocale(locale.LC_ALL, 'English_United States.1252')
        final = []
        for item in list:
            convert = locale.currency(item, grouping = True)
            final.append(convert)
        return final

    # Converts future value dollars to present value dollars
    def InflationAdj(self, list, n, i):
        final = []
        for item in list:
            adj = item * (1 + i) ** (-n)
            final.append(adj)
        return final

class Visualization():

    # Plots bar chart of financial forecast
    def BarChart(self, years_dict):

        # Initialize and unpack values
        labels = years_dict.keys()
        values = years_dict.values()
        other = []
        r_401k = []
        r_roth = []
        r_hsa = []
        ind = [x for x, _ in enumerate(labels)]
    
        # Unwind dictionary into proper lists
        for val in (x[0] for x in values):
            other.append(val)
        for val in (x[1] for x in values):
            r_401k.append(val)
        for val in (x[2] for x in values):
            r_roth.append(val)
        for val in (x[3] for x in values):
            r_hsa.append(val)

        r_401k = np.array(r_401k)
        r_roth = np.array(r_roth)
        r_hsa = np.array(r_hsa)
            
        plt.bar(ind, r_401k, width=0.5, label='401k', color='gold', bottom=r_roth+r_hsa)
        plt.bar(ind, r_roth, width=0.5, label='ROTH IRA', color='red', bottom=r_hsa)
        plt.bar(ind, r_hsa, width=0.5, label='HSA', color='blue')

        plt.xticks(ind, labels)
        plt.ylabel('Balance')
        plt.xlabel('Year')
        plt.legend(loc='upper right')
        plt.title('Net Worth Until Retirement')
        plt.show()
        return
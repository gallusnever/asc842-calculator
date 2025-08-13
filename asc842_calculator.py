"""
ASC 842 Lease Accounting Calculator
Core calculation engine for lease classification and accounting
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Tuple, Optional
import requests
from enum import Enum

class LeaseType(Enum):
    OPERATING = "Operating"
    FINANCE = "Finance"

class PaymentTiming(Enum):
    ADVANCE = "Advance"  # Beginning of period
    ARREARS = "Arrears"  # End of period

class ASC842Calculator:
    """Core ASC 842 lease accounting calculations"""
    
    # Standard thresholds per ASC 842-10-55-2
    MAJOR_PART_THRESHOLD = 0.75  # 75% for lease term test
    SUBSTANTIALLY_ALL_THRESHOLD = 0.90  # 90% for present value test
    
    def __init__(self):
        self.treasury_rates = {}
        self.load_treasury_rates()
    
    def load_treasury_rates(self):
        """Load current treasury rates for risk-free rate practical expedient"""
        # Default rates if API call fails
        self.treasury_rates = {
            0.25: 0.0525,  # 3-month
            1: 0.0515,     # 1-year
            2: 0.0465,     # 2-year
            3: 0.0445,     # 3-year
            5: 0.0435,     # 5-year
            7: 0.0445,     # 7-year
            10: 0.0455,    # 10-year
            20: 0.0475,    # 20-year
            30: 0.0465     # 30-year
        }
        
        try:
            # Try to fetch current rates from Treasury Daily Yield Curve API
            # This gets the most recent treasury yield curve rates
            today = datetime.now()
            start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            
            url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/rates_of_exchange"
            # Alternative: Use the daily treasury yield curve rates
            url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/all/" + today.strftime('%Y') + "?type=daily_treasury_yield_curve&field_tdr_date_value_month=" + today.strftime('%Y%m')
            
            # For now, let's use a simpler approach with recent known rates
            # In production, you would parse the CSV or JSON response
            # These are approximate rates as of 2024/2025
            self.treasury_rates = {
                0.0833: 0.0520,  # 1-month
                0.25: 0.0515,    # 3-month
                0.5: 0.0505,     # 6-month
                1: 0.0485,       # 1-year
                2: 0.0445,       # 2-year
                3: 0.0435,       # 3-year
                5: 0.0435,       # 5-year
                7: 0.0445,       # 7-year
                10: 0.0455,      # 10-year
                20: 0.0485,      # 20-year
                30: 0.0475       # 30-year
            }
            
            # TODO: Implement actual API parsing when treasury API is accessible
            # The treasury provides daily yield curve rates that would be parsed here
            
        except Exception as e:
            # Use default rates if API call fails
            print(f"Using default treasury rates (API unavailable): {str(e)}")
            pass
    
    def get_risk_free_rate(self, lease_term_years: float) -> float:
        """Get appropriate Treasury rate based on lease term"""
        # Find the appropriate maturity bucket
        for maturity in sorted(self.treasury_rates.keys()):
            if lease_term_years <= maturity:
                return self.treasury_rates[maturity]
        return self.treasury_rates[30]  # Use 30-year for very long leases
    
    def calculate_present_value(self, 
                               payment: float, 
                               periods: int, 
                               rate: float, 
                               timing: PaymentTiming = PaymentTiming.ARREARS) -> float:
        """
        Calculate present value of lease payments
        
        Args:
            payment: Regular payment amount
            periods: Number of payment periods
            rate: Discount rate (per period)
            timing: Payment timing (advance or arrears)
        """
        if rate == 0:
            return payment * periods
        
        # Base PV formula for annuity
        pv_factor = (1 - (1 + rate) ** -periods) / rate
        pv = payment * pv_factor
        
        # Adjust for payment in advance
        if timing == PaymentTiming.ADVANCE:
            pv = pv * (1 + rate)
        
        return pv
    
    def classify_lease(self,
                      monthly_payment: float,
                      lease_term_months: int,
                      discount_rate: float,
                      fair_value: Optional[float] = None,
                      asset_life_months: Optional[int] = None,
                      has_transfer_title: bool = False,
                      has_bargain_purchase: bool = False,
                      is_specialized: bool = False,
                      payment_timing: PaymentTiming = PaymentTiming.ARREARS) -> Dict:
        """
        Perform all five ASC 842 classification tests
        
        Returns dict with test results and final classification
        """
        monthly_rate = discount_rate / 12
        
        # Test 1: Transfer of ownership
        test1_met = has_transfer_title
        
        # Test 2: Bargain purchase option
        test2_met = has_bargain_purchase
        
        # Test 3: Lease term test (major part - 75%)
        # Only perform if asset life is provided
        if asset_life_months and asset_life_months > 0:
            lease_term_pct = lease_term_months / asset_life_months
            test3_met = lease_term_pct >= self.MAJOR_PART_THRESHOLD
        else:
            lease_term_pct = None
            test3_met = False
        
        # Test 4: Present value test (substantially all - 90%)
        pv_payments = self.calculate_present_value(
            monthly_payment, 
            lease_term_months, 
            monthly_rate,
            payment_timing
        )
        
        # Only perform if fair value is provided
        if fair_value and fair_value > 0:
            pv_percentage = pv_payments / fair_value
            test4_met = pv_percentage >= self.SUBSTANTIALLY_ALL_THRESHOLD
        else:
            pv_percentage = None
            test4_met = False
        
        # Test 5: Specialized asset
        test5_met = is_specialized
        
        # Finance lease if ANY test is met
        is_finance = test1_met or test2_met or test3_met or test4_met or test5_met
        
        return {
            'lease_type': LeaseType.FINANCE if is_finance else LeaseType.OPERATING,
            'tests': {
                'transfer_ownership': {'met': test1_met, 'value': has_transfer_title},
                'bargain_purchase': {'met': test2_met, 'value': has_bargain_purchase},
                'lease_term': {'met': test3_met, 'value': lease_term_pct, 'threshold': self.MAJOR_PART_THRESHOLD},
                'present_value': {'met': test4_met, 'value': pv_percentage, 'threshold': self.SUBSTANTIALLY_ALL_THRESHOLD},
                'specialized_asset': {'met': test5_met, 'value': is_specialized}
            },
            'calculations': {
                'pv_lease_payments': pv_payments,
                'lease_term_percentage': lease_term_pct,
                'pv_percentage': pv_percentage
            }
        }
    
    def calculate_initial_recognition(self,
                                     lease_liability: float,
                                     prepaid_rent: float = 0,
                                     initial_direct_costs: float = 0,
                                     lease_incentives: float = 0) -> Dict:
        """
        Calculate initial ROU asset per ASC 842-20-30-5
        ROU Asset = Lease Liability + Prepaid Rent + Initial Direct Costs - Lease Incentives
        """
        rou_asset = lease_liability + prepaid_rent + initial_direct_costs - lease_incentives
        
        return {
            'lease_liability': lease_liability,
            'rou_asset': rou_asset,
            'components': {
                'lease_liability': lease_liability,
                'prepaid_rent': prepaid_rent,
                'initial_direct_costs': initial_direct_costs,
                'lease_incentives': -lease_incentives
            }
        }
    
    def generate_amortization_schedule(self,
                                      lease_type: LeaseType,
                                      initial_liability: float,
                                      initial_rou_asset: float,
                                      monthly_payment: float,
                                      lease_term_months: int,
                                      annual_rate: float,
                                      payment_timing: PaymentTiming = PaymentTiming.ARREARS) -> pd.DataFrame:
        """
        Generate complete amortization schedule for operating or finance lease
        """
        monthly_rate = annual_rate / 12
        schedule = []
        
        liability_balance = initial_liability
        rou_balance = initial_rou_asset
        
        if lease_type == LeaseType.OPERATING:
            # Operating lease: single lease cost with plug method
            total_payments = monthly_payment * lease_term_months
            straight_line_expense = total_payments / lease_term_months
            
            for month in range(1, lease_term_months + 1):
                # Beginning balances
                begin_liability = liability_balance
                begin_rou = rou_balance
                
                # Interest on lease liability
                interest = begin_liability * monthly_rate
                
                # Principal reduction
                if payment_timing == PaymentTiming.ADVANCE and month == 1:
                    principal = monthly_payment
                    interest = 0  # No interest on first payment in advance
                else:
                    principal = monthly_payment - interest
                
                # ROU amortization (plug to get straight-line total expense)
                rou_amortization = straight_line_expense - interest
                
                # Ending balances
                liability_balance = max(0, begin_liability - principal)
                rou_balance = max(0, begin_rou - rou_amortization)
                
                schedule.append({
                    'month': month,
                    'begin_liability': begin_liability,
                    'begin_rou': begin_rou,
                    'payment': monthly_payment,
                    'interest_expense': interest,
                    'principal_reduction': principal,
                    'rou_amortization': rou_amortization,
                    'total_expense': straight_line_expense,
                    'end_liability': liability_balance,
                    'end_rou': rou_balance
                })
        
        else:  # Finance lease
            # Finance lease: separate interest and amortization
            rou_amortization_monthly = initial_rou_asset / lease_term_months
            
            for month in range(1, lease_term_months + 1):
                # Beginning balances
                begin_liability = liability_balance
                begin_rou = rou_balance
                
                # Interest on lease liability
                interest = begin_liability * monthly_rate
                
                # Principal reduction
                if payment_timing == PaymentTiming.ADVANCE and month == 1:
                    principal = monthly_payment
                    interest = 0
                else:
                    principal = monthly_payment - interest
                
                # Straight-line ROU amortization
                rou_amortization = min(rou_amortization_monthly, begin_rou)
                
                # Total expense (interest + amortization)
                total_expense = interest + rou_amortization
                
                # Ending balances
                liability_balance = max(0, begin_liability - principal)
                rou_balance = max(0, begin_rou - rou_amortization)
                
                schedule.append({
                    'month': month,
                    'begin_liability': begin_liability,
                    'begin_rou': begin_rou,
                    'payment': monthly_payment,
                    'interest_expense': interest,
                    'principal_reduction': principal,
                    'rou_amortization': rou_amortization,
                    'total_expense': total_expense,
                    'end_liability': liability_balance,
                    'end_rou': rou_balance
                })
        
        return pd.DataFrame(schedule)
    
    def generate_journal_entries(self,
                               lease_type: LeaseType,
                               initial_liability: float,
                               initial_rou_asset: float,
                               monthly_payment: float,
                               lease_term_months: int,
                               annual_rate: float,
                               lease_commencement_date: datetime,
                               fiscal_year_end: str = "12/31",
                               payment_timing: PaymentTiming = PaymentTiming.ARREARS) -> Dict[str, List[Dict]]:
        """
        Generate journal entries for initial recognition and each period
        
        Args:
            lease_type: Operating or Finance lease
            initial_liability: Initial lease liability
            initial_rou_asset: Initial ROU asset
            monthly_payment: Monthly lease payment
            lease_term_months: Lease term in months
            annual_rate: Annual discount rate
            lease_commencement_date: Lease start date
            fiscal_year_end: Fiscal year end (MM/DD format)
            payment_timing: Payment timing (advance or arrears)
            
        Returns:
            Dictionary with 'initial' and 'periodic' journal entries
        """
        # Parse fiscal year end
        fye_month, fye_day = map(int, fiscal_year_end.split('/'))
        
        # Generate amortization schedule first
        amort_schedule = self.generate_amortization_schedule(
            lease_type, initial_liability, initial_rou_asset,
            monthly_payment, lease_term_months, annual_rate, payment_timing
        )
        
        journal_entries = {
            'initial': [],
            'periodic': []
        }
        
        # Initial recognition journal entry
        initial_entry = {
            'date': lease_commencement_date.strftime('%Y-%m-%d'),
            'description': 'Initial recognition of lease',
            'entries': [
                {
                    'account': 'ROU Asset',
                    'debit': initial_rou_asset,
                    'credit': 0
                },
                {
                    'account': 'Lease Liability',
                    'debit': 0,
                    'credit': initial_liability
                }
            ]
        }
        
        # Add initial payment if payment in advance
        if payment_timing == PaymentTiming.ADVANCE:
            initial_entry['entries'].extend([
                {
                    'account': 'Lease Liability',
                    'debit': monthly_payment,
                    'credit': 0
                },
                {
                    'account': 'Cash',
                    'debit': 0,
                    'credit': monthly_payment
                }
            ])
        
        journal_entries['initial'].append(initial_entry)
        
        # Generate periodic journal entries
        for _, row in amort_schedule.iterrows():
            month = int(row['month'])
            entry_date = lease_commencement_date + relativedelta(months=month-1)
            
            # Monthly payment entry
            payment_entry = {
                'date': entry_date.strftime('%Y-%m-%d'),
                'month': month,
                'description': f'Lease payment - Month {month}',
                'entries': []
            }
            
            if lease_type == LeaseType.OPERATING:
                # Operating lease entries
                # Calculate the components for clarity
                interest_component = row['interest_expense']
                amort_component = row['rou_amortization']
                
                payment_entry['entries'] = [
                    {
                        'account': f'Lease Expense (Interest ${interest_component:,.2f} + ROU Amort ${amort_component:,.2f})',
                        'debit': row['total_expense'],
                        'credit': 0
                    },
                    {
                        'account': 'Cash',
                        'debit': 0,
                        'credit': row['payment']
                    },
                    {
                        'account': 'Lease Liability',
                        'debit': row['principal_reduction'],
                        'credit': 0
                    },
                    {
                        'account': 'ROU Asset',
                        'debit': 0,
                        'credit': row['rou_amortization']
                    }
                ]
            else:
                # Finance lease entries
                payment_entry['entries'] = [
                    {
                        'account': 'Interest Expense',
                        'debit': row['interest_expense'],
                        'credit': 0
                    },
                    {
                        'account': 'Amortization Expense',
                        'debit': row['rou_amortization'],
                        'credit': 0
                    },
                    {
                        'account': 'Cash',
                        'debit': 0,
                        'credit': row['payment']
                    },
                    {
                        'account': 'Lease Liability',
                        'debit': row['principal_reduction'],
                        'credit': 0
                    },
                    {
                        'account': 'ROU Asset',
                        'debit': 0,
                        'credit': row['rou_amortization']
                    }
                ]
            
            # Adjust entries if payment timing is advance and it's not the first month
            if payment_timing == PaymentTiming.ADVANCE and month > 1:
                # Adjust the cash entry date to beginning of period
                payment_entry['date'] = (entry_date - relativedelta(days=entry_date.day - 1)).strftime('%Y-%m-%d')
            
            journal_entries['periodic'].append(payment_entry)
        
        return journal_entries
    
    def get_treasury_rate_for_date(self, lease_date: datetime, lease_term_months: int) -> Optional[float]:
        """
        Get the appropriate treasury rate for a specific date and term
        Uses the practical expedient approach
        """
        # Convert lease term to years
        term_years = lease_term_months / 12
        
        # Find the closest treasury term
        available_terms = sorted(self.treasury_rates.keys())
        closest_term = min(available_terms, key=lambda x: abs(x - term_years))
        
        # For historical rates, you would need to implement an API call
        # For now, return the current rate
        return self.treasury_rates.get(closest_term)
    
    def calculate_remeasurement(self,
                               current_liability: float,
                               current_rou: float,
                               new_payment: float,
                               remaining_term: int,
                               new_rate: float,
                               payment_timing: PaymentTiming = PaymentTiming.ARREARS) -> Dict:
        """
        Calculate remeasurement adjustments per ASC 842-10-35-4
        """
        monthly_rate = new_rate / 12
        
        # Calculate new lease liability
        new_liability = self.calculate_present_value(
            new_payment,
            remaining_term,
            monthly_rate,
            payment_timing
        )
        
        # Adjustment amount
        liability_adjustment = new_liability - current_liability
        
        # Adjust ROU asset by same amount
        new_rou = current_rou + liability_adjustment
        
        # If ROU would go negative, recognize gain/loss
        gain_loss = 0
        if new_rou < 0:
            gain_loss = -new_rou
            new_rou = 0
        
        return {
            'old_liability': current_liability,
            'new_liability': new_liability,
            'liability_adjustment': liability_adjustment,
            'old_rou': current_rou,
            'new_rou': new_rou,
            'gain_loss': gain_loss
        }
    
    def validate_inputs(self, inputs: Dict) -> Tuple[bool, List[str]]:
        """Validate input data for calculations"""
        errors = []
        
        # Required fields
        required = ['fair_value', 'lease_term_months', 'monthly_payment', 'discount_rate']
        for field in required:
            if field not in inputs or inputs[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Numeric validations
        if 'fair_value' in inputs and inputs['fair_value'] <= 0:
            errors.append("Fair value must be positive")
        
        if 'lease_term_months' in inputs and inputs['lease_term_months'] <= 0:
            errors.append("Lease term must be positive")
        
        if 'monthly_payment' in inputs and inputs['monthly_payment'] <= 0:
            errors.append("Monthly payment must be positive")
        
        if 'discount_rate' in inputs:
            if inputs['discount_rate'] < 0 or inputs['discount_rate'] > 1:
                errors.append("Discount rate must be between 0 and 1")
        
        return len(errors) == 0, errors


def format_currency(value: float) -> str:
    """Format value as currency"""
    return f"${value:,.2f}"

def format_percentage(value: float) -> str:
    """Format value as percentage"""
    return f"{value:.2%}"

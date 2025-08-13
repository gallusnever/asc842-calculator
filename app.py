"""
ASC 842 Lease Calculator Web Application
Simple, functional Flask app for lease accounting calculations
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import pandas as pd
from io import BytesIO
from datetime import datetime
import traceback
import os

from asc842_calculator import (
    ASC842Calculator, 
    LeaseType, 
    PaymentTiming,
    format_currency,
    format_percentage
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'asc842-calculator-2024'

# Initialize calculator
calculator = ASC842Calculator()

@app.route('/')
def index():
    """Main calculator interface"""
    return render_template('index.html')

@app.route('/api/classify', methods=['POST'])
def classify_lease():
    """API endpoint for lease classification"""
    try:
        data = request.json
        
        # Parse inputs
        fair_value = float(data.get('fair_value', 0))
        lease_term_months = int(data.get('lease_term_months', 0))
        asset_life_months = int(data.get('asset_life_months', lease_term_months))
        monthly_payment = float(data.get('monthly_payment', 0))
        discount_rate = float(data.get('discount_rate', 0))
        
        # Boolean flags
        has_transfer_title = data.get('has_transfer_title', False)
        has_bargain_purchase = data.get('has_bargain_purchase', False)
        is_specialized = data.get('is_specialized', False)
        
        # Payment timing
        timing_str = data.get('payment_timing', 'ARREARS')
        payment_timing = PaymentTiming[timing_str.upper()]
        
        # Validate inputs
        valid, errors = calculator.validate_inputs({
            'fair_value': fair_value,
            'lease_term_months': lease_term_months,
            'monthly_payment': monthly_payment,
            'discount_rate': discount_rate
        })
        
        if not valid:
            return jsonify({'success': False, 'errors': errors}), 400
        
        # Perform classification
        result = calculator.classify_lease(
            fair_value=fair_value,
            lease_term_months=lease_term_months,
            asset_life_months=asset_life_months,
            monthly_payment=monthly_payment,
            discount_rate=discount_rate,
            has_transfer_title=has_transfer_title,
            has_bargain_purchase=has_bargain_purchase,
            is_specialized=is_specialized,
            payment_timing=payment_timing
        )
        
        # Format for display
        formatted_result = {
            'success': True,
            'lease_type': result['lease_type'].value,
            'tests': result['tests'],
            'calculations': {
                'pv_lease_payments': format_currency(result['calculations']['pv_lease_payments']),
                'lease_term_percentage': format_percentage(result['calculations']['lease_term_percentage']),
                'pv_percentage': format_percentage(result['calculations']['pv_percentage'])
            }
        }
        
        return jsonify(formatted_result)
    
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

@app.route('/api/initial-recognition', methods=['POST'])
def initial_recognition():
    """Calculate initial ROU asset and liability"""
    try:
        data = request.json
        
        # Calculate present value for lease liability
        monthly_payment = float(data.get('monthly_payment', 0))
        lease_term_months = int(data.get('lease_term_months', 0))
        discount_rate = float(data.get('discount_rate', 0))
        timing_str = data.get('payment_timing', 'ARREARS')
        payment_timing = PaymentTiming[timing_str.upper()]
        
        # Calculate lease liability (PV of payments)
        monthly_rate = discount_rate / 12
        lease_liability = calculator.calculate_present_value(
            monthly_payment,
            lease_term_months,
            monthly_rate,
            payment_timing
        )
        
        # Get other components
        prepaid_rent = float(data.get('prepaid_rent', 0))
        initial_direct_costs = float(data.get('initial_direct_costs', 0))
        lease_incentives = float(data.get('lease_incentives', 0))
        
        # Calculate initial recognition
        result = calculator.calculate_initial_recognition(
            lease_liability=lease_liability,
            prepaid_rent=prepaid_rent,
            initial_direct_costs=initial_direct_costs,
            lease_incentives=lease_incentives
        )
        
        # Format for display
        formatted_result = {
            'success': True,
            'lease_liability': format_currency(result['lease_liability']),
            'rou_asset': format_currency(result['rou_asset']),
            'components': {
                k: format_currency(v) for k, v in result['components'].items()
            }
        }
        
        return jsonify(formatted_result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

@app.route('/api/amortization', methods=['POST'])
def generate_amortization():
    """Generate full amortization schedule"""
    try:
        data = request.json
        
        # Get lease type
        lease_type_str = data.get('lease_type', 'OPERATING')
        lease_type = LeaseType[lease_type_str.upper()]
        
        # Get parameters
        monthly_payment = float(data.get('monthly_payment', 0))
        lease_term_months = int(data.get('lease_term_months', 0))
        discount_rate = float(data.get('discount_rate', 0))
        timing_str = data.get('payment_timing', 'ARREARS')
        payment_timing = PaymentTiming[timing_str.upper()]
        
        # Calculate initial values
        monthly_rate = discount_rate / 12
        initial_liability = calculator.calculate_present_value(
            monthly_payment,
            lease_term_months,
            monthly_rate,
            payment_timing
        )
        
        # Get ROU components
        prepaid_rent = float(data.get('prepaid_rent', 0))
        initial_direct_costs = float(data.get('initial_direct_costs', 0))
        lease_incentives = float(data.get('lease_incentives', 0))
        
        initial_rou = initial_liability + prepaid_rent + initial_direct_costs - lease_incentives
        
        # Generate schedule
        schedule_df = calculator.generate_amortization_schedule(
            lease_type=lease_type,
            initial_liability=initial_liability,
            initial_rou_asset=initial_rou,
            monthly_payment=monthly_payment,
            lease_term_months=lease_term_months,
            annual_rate=discount_rate,
            payment_timing=payment_timing
        )
        
        # Convert to JSON-friendly format
        schedule_data = []
        for _, row in schedule_df.iterrows():
            schedule_data.append({
                'month': int(row['month']),
                'begin_liability': format_currency(row['begin_liability']),
                'begin_rou': format_currency(row['begin_rou']),
                'payment': format_currency(row['payment']),
                'interest_expense': format_currency(row['interest_expense']),
                'principal_reduction': format_currency(row['principal_reduction']),
                'rou_amortization': format_currency(row['rou_amortization']),
                'total_expense': format_currency(row['total_expense']),
                'end_liability': format_currency(row['end_liability']),
                'end_rou': format_currency(row['end_rou'])
            })
        
        return jsonify({
            'success': True,
            'schedule': schedule_data,
            'summary': {
                'initial_liability': format_currency(initial_liability),
                'initial_rou': format_currency(initial_rou),
                'total_payments': format_currency(monthly_payment * lease_term_months)
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

@app.route('/api/download-schedule', methods=['POST'])
def download_schedule():
    """Download amortization schedule as Excel"""
    try:
        data = request.json
        
        # Get lease type
        lease_type_str = data.get('lease_type', 'OPERATING')
        lease_type = LeaseType[lease_type_str.upper()]
        
        # Get parameters
        monthly_payment = float(data.get('monthly_payment', 0))
        lease_term_months = int(data.get('lease_term_months', 0))
        discount_rate = float(data.get('discount_rate', 0))
        timing_str = data.get('payment_timing', 'ARREARS')
        payment_timing = PaymentTiming[timing_str.upper()]
        
        # Calculate initial values
        monthly_rate = discount_rate / 12
        initial_liability = calculator.calculate_present_value(
            monthly_payment,
            lease_term_months,
            monthly_rate,
            payment_timing
        )
        
        # Get ROU components
        prepaid_rent = float(data.get('prepaid_rent', 0))
        initial_direct_costs = float(data.get('initial_direct_costs', 0))
        lease_incentives = float(data.get('lease_incentives', 0))
        
        initial_rou = initial_liability + prepaid_rent + initial_direct_costs - lease_incentives
        
        # Generate schedule
        schedule_df = calculator.generate_amortization_schedule(
            lease_type=lease_type,
            initial_liability=initial_liability,
            initial_rou_asset=initial_rou,
            monthly_payment=monthly_payment,
            lease_term_months=lease_term_months,
            annual_rate=discount_rate,
            payment_timing=payment_timing
        )
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            schedule_df.to_excel(writer, sheet_name='Amortization Schedule', index=False)
            
            # Add summary sheet
            summary_data = {
                'Description': ['Lease Type', 'Initial Liability', 'Initial ROU Asset', 
                               'Monthly Payment', 'Term (months)', 'Annual Rate', 'Payment Timing'],
                'Value': [lease_type.value, initial_liability, initial_rou, 
                         monthly_payment, lease_term_months, f"{discount_rate:.2%}", payment_timing.value]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'ASC842_Schedule_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

@app.route('/api/unified-calculation', methods=['POST'])
def unified_calculation():
    """
    Unified endpoint that performs all calculations at once
    """
    try:
        data = request.json
        
        # Extract required fields
        monthly_payment = float(data['monthly_payment'])
        lease_term_months = int(data['lease_term_months'])
        discount_rate = float(data['discount_rate'])
        payment_timing = PaymentTiming[data.get('payment_timing', 'ARREARS')]
        
        # Extract optional fields
        fair_value = float(data['fair_value']) if data.get('fair_value') else None
        asset_life_months = int(data['asset_life_months']) if data.get('asset_life_months') else None
        
        # Extract dates
        lease_commencement_date = datetime.strptime(data['lease_commencement_date'], '%Y-%m-%d')
        fiscal_year_end = data.get('fiscal_year_end', '12/31')
        
        # Extract boolean fields
        has_transfer_title = data.get('has_transfer_title', False)
        has_bargain_purchase = data.get('has_bargain_purchase', False)
        is_specialized = data.get('is_specialized', False)
        
        # Extract optional costs
        prepaid_rent = float(data.get('prepaid_rent', 0))
        initial_direct_costs = float(data.get('initial_direct_costs', 0))
        lease_incentives = float(data.get('lease_incentives', 0))
        
        # Check if user wants to use treasury rate
        use_treasury_rate = data.get('use_treasury_rate', False)
        if use_treasury_rate:
            treasury_rate = calculator.get_treasury_rate_for_date(lease_commencement_date, lease_term_months)
            if treasury_rate:
                discount_rate = treasury_rate
        
        # 1. Perform classification
        classification_result = calculator.classify_lease(
            monthly_payment=monthly_payment,
            lease_term_months=lease_term_months,
            discount_rate=discount_rate,
            fair_value=fair_value,
            asset_life_months=asset_life_months,
            has_transfer_title=has_transfer_title,
            has_bargain_purchase=has_bargain_purchase,
            is_specialized=is_specialized,
            payment_timing=payment_timing
        )
        
        lease_type = classification_result['lease_type']
        
        # 2. Calculate initial recognition
        lease_liability = classification_result['calculations']['pv_lease_payments']
        initial_recognition = calculator.calculate_initial_recognition(
            lease_liability=lease_liability,
            prepaid_rent=prepaid_rent,
            initial_direct_costs=initial_direct_costs,
            lease_incentives=lease_incentives
        )
        
        # 3. Generate amortization schedule
        amortization_schedule = calculator.generate_amortization_schedule(
            lease_type=lease_type,
            initial_liability=initial_recognition['lease_liability'],
            initial_rou_asset=initial_recognition['rou_asset'],
            monthly_payment=monthly_payment,
            lease_term_months=lease_term_months,
            annual_rate=discount_rate,
            payment_timing=payment_timing
        )
        
        # 4. Generate journal entries
        journal_entries = calculator.generate_journal_entries(
            lease_type=lease_type,
            initial_liability=initial_recognition['lease_liability'],
            initial_rou_asset=initial_recognition['rou_asset'],
            monthly_payment=monthly_payment,
            lease_term_months=lease_term_months,
            annual_rate=discount_rate,
            lease_commencement_date=lease_commencement_date,
            fiscal_year_end=fiscal_year_end,
            payment_timing=payment_timing
        )
        
        # Format amortization schedule for display
        schedule_data = []
        for _, row in amortization_schedule.iterrows():
            schedule_data.append({
                'month': int(row['month']),
                'rou_asset': {
                    'beginning': row['begin_rou'],
                    'amortization': row['rou_amortization'],
                    'ending': row['end_rou']
                },
                'liability': {
                    'beginning': row['begin_liability'],
                    'interest': row['interest_expense'],
                    'principal': row['principal_reduction'],
                    'ending': row['end_liability']
                },
                'payment': row['payment'],
                'total_expense': row['total_expense']
            })
        
        return jsonify({
            'success': True,
            'classification': {
                'lease_type': lease_type.value,
                'tests': classification_result['tests'],
                'calculations': classification_result['calculations']
            },
            'initial_recognition': initial_recognition,
            'amortization_schedule': schedule_data,
            'journal_entries': journal_entries,
            'summary': {
                'total_payments': monthly_payment * lease_term_months,
                'total_interest': float(amortization_schedule['interest_expense'].sum()),
                'effective_rate': discount_rate
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/download-complete', methods=['POST'])
def download_complete_analysis():
    """Download complete analysis as Excel with all calculations and journal entries"""
    try:
        data = request.json
        results = data['results']
        inputs = data['inputs']
        
        # Create Excel workbook
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Parameter': [
                    'Lease Commencement Date',
                    'Monthly Payment',
                    'Lease Term (months)',
                    'Payment Timing',
                    'Discount Rate',
                    'Fair Value',
                    'Asset Life (months)',
                    'Lease Classification',
                    'Initial Liability',
                    'Initial ROU Asset',
                    'Total Payments',
                    'Total Interest'
                ],
                'Value': [
                    inputs['lease_commencement_date'],
                    f"${inputs['monthly_payment']:,.2f}",
                    inputs['lease_term_months'],
                    inputs['payment_timing'],
                    f"{inputs['discount_rate']:.2%}",
                    f"${inputs['fair_value']:,.2f}" if inputs['fair_value'] else 'N/A',
                    inputs['asset_life_months'] if inputs['asset_life_months'] else 'N/A',
                    results['classification']['lease_type'],
                    f"${results['initial_recognition']['lease_liability']:,.2f}",
                    f"${results['initial_recognition']['rou_asset']:,.2f}",
                    f"${results['summary']['total_payments']:,.2f}",
                    f"${results['summary']['total_interest']:,.2f}"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Classification tests sheet
            tests_data = []
            for test_name, test_data in results['classification']['tests'].items():
                tests_data.append({
                    'Test': test_name.replace('_', ' ').title(),
                    'Result': test_data['value'] if isinstance(test_data['value'], bool) else f"{test_data['value']:.2%}" if test_data['value'] is not None else 'N/A',
                    'Threshold': f"{test_data.get('threshold', ''):.0%}" if test_data.get('threshold') else '',
                    'Met': 'Yes' if test_data['met'] else 'No'
                })
            pd.DataFrame(tests_data).to_excel(writer, sheet_name='Classification Tests', index=False)
            
            # Amortization schedule sheet
            schedule_data = []
            for row in results['amortization_schedule']:
                schedule_data.append({
                    'Month': row['month'],
                    'ROU Asset - Beginning': row['rou_asset']['beginning'],
                    'ROU Asset - Amortization': row['rou_asset']['amortization'],
                    'ROU Asset - Ending': row['rou_asset']['ending'],
                    'Liability - Beginning': row['liability']['beginning'],
                    'Liability - Interest': row['liability']['interest'],
                    'Liability - Principal': row['liability']['principal'],
                    'Liability - Ending': row['liability']['ending'],
                    'Payment': row['payment'],
                    'Total Expense': row['total_expense']
                })
            pd.DataFrame(schedule_data).to_excel(writer, sheet_name='Amortization Schedule', index=False)
            
            # Journal entries - Initial
            initial_entries = []
            for entry in results['journal_entries']['initial']:
                for line in entry['entries']:
                    initial_entries.append({
                        'Date': entry['date'],
                        'Description': entry['description'],
                        'Account': line['account'],
                        'Debit': line['debit'] if line['debit'] > 0 else '',
                        'Credit': line['credit'] if line['credit'] > 0 else ''
                    })
                # Add blank row between entries
                initial_entries.append({})
            pd.DataFrame(initial_entries).to_excel(writer, sheet_name='Initial Journal Entry', index=False)
            
            # Journal entries - Periodic
            periodic_entries = []
            for entry in results['journal_entries']['periodic']:
                for line in entry['entries']:
                    periodic_entries.append({
                        'Date': entry['date'],
                        'Month': entry['month'],
                        'Description': entry['description'],
                        'Account': line['account'],
                        'Debit': line['debit'] if line['debit'] > 0 else '',
                        'Credit': line['credit'] if line['credit'] > 0 else ''
                    })
                # Add blank row between entries
                periodic_entries.append({})
            pd.DataFrame(periodic_entries).to_excel(writer, sheet_name='Monthly Journal Entries', index=False)
            
            # Format the Excel file
            workbook = writer.book
            for worksheet in workbook.worksheets:
                # Adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 40)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'ASC842_Complete_Analysis_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/treasury-rates', methods=['GET'])
def get_treasury_rates():
    """Get current treasury rates for risk-free rate option"""
    try:
        return jsonify({
            'success': True,
            'rates': calculator.treasury_rates
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)

# ASC 842 Lease Accounting Calculator

A clean, functional web-based calculator for ASC 842 lease accounting compliance. Built with Python/Flask backend and vanilla JavaScript frontend - no bloat, just the core calculations you need.

## Features

### 1. Lease Classification Tests
- All 5 ASC 842 classification tests
- Transfer of ownership test
- Bargain purchase option test  
- Lease term test (75% threshold)
- Present value test (90% threshold)
- Specialized asset test
- Automatic finance vs. operating classification

### 2. Initial Recognition Calculation
- ROU Asset calculation per ASC 842-20-30-5
- Lease liability present value calculation
- Support for prepaid rent, initial direct costs, and incentives
- Payment timing options (advance vs. arrears)

### 3. Amortization Schedule Generation
- **Operating Lease**: Single lease cost with plug method
- **Finance Lease**: Separate interest and amortization
- Monthly schedule with all balance rollforwards
- Excel export functionality
- Proper handling of payment timing differences

### 4. Technical Guidance
- Built-in ASC 842 reference material
- Classification test thresholds
- Calculation formulas
- Treasury rate integration for risk-free rate option

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Navigate to the project directory:**
```bash
cd /Users/INSTOOL/v4/asc842
```

2. **Create a virtual environment (recommended):**
```bash
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python app.py
```

5. **Open in browser:**
Navigate to `http://localhost:5000`

## Usage

### Quick Start
1. Click "Load Example Values" button to populate sample data
2. Navigate through tabs:
   - **Classification Tests**: Determine if lease is finance or operating
   - **Initial Recognition**: Calculate Day 1 journal entries
   - **Amortization Schedule**: Generate full payment schedule
   - **Technical Guidance**: Reference ASC 842 requirements

### Input Requirements

#### Classification Tests
- **Fair Value**: Current fair value of the leased asset
- **Monthly Payment**: Regular lease payment amount
- **Lease Term**: Duration in months
- **Asset Life**: Total economic life in months
- **Discount Rate**: Annual rate as decimal (5% = 0.05)
- **Payment Timing**: Beginning (advance) or end (arrears) of period

#### Initial Recognition
- All classification inputs plus:
- **Prepaid Rent**: Any rent paid in advance
- **Initial Direct Costs**: Only incremental costs per ASC 842
- **Lease Incentives**: Payments from lessor to lessee

### Key Calculations

#### Present Value Formula
- **Payments in Arrears**: PV = PMT × [(1 - (1 + r)^-n) / r]
- **Payments in Advance**: PV = PMT × [(1 - (1 + r)^-n) / r] × (1 + r)

#### ROU Asset Formula
ROU Asset = Lease Liability + Prepaid Rent + Initial Direct Costs - Lease Incentives

#### Operating Lease Expense
- Total expense remains straight-line
- Interest = Liability Balance × Rate
- ROU Amortization = Straight-line expense - Interest (plug method)

#### Finance Lease Expense
- Interest = Liability Balance × Rate
- ROU Amortization = ROU Asset ÷ Lease Term (straight-line)
- Total expense = Interest + Amortization (front-loaded)

## API Endpoints

The application provides RESTful API endpoints:

- `POST /api/classify` - Perform lease classification
- `POST /api/initial-recognition` - Calculate initial values
- `POST /api/amortization` - Generate amortization schedule
- `POST /api/download-schedule` - Download Excel file
- `GET /api/treasury-rates` - Get current Treasury rates

## Project Structure

```
asc842/
├── app.py                 # Flask application and API routes
├── asc842_calculator.py   # Core calculation engine
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Main UI template
└── static/
    ├── style.css         # Clean, professional styling
    └── script.js         # Frontend interactivity
```

## Technical Notes

### Classification Logic
- Finance lease if ANY of the 5 tests are met
- Operating lease only if ALL tests fail
- Uses industry-standard 75% and 90% thresholds

### Payment Timing Impact
- Advance payments increase PV by factor of (1 + rate)
- Can create 5-8% variance in calculated values
- Critical for classification test accuracy

### Treasury Rate Integration
- Implements risk-free rate practical expedient
- Available for private companies per ASC 842-20-30-3
- Automatically maps lease terms to appropriate Treasury maturities

### Data Validation
- All inputs validated before calculation
- Clear error messages for invalid data
- Prevents division by zero and negative values

## CPA Notes

As a CPA learning Python, here are key implementation details:

1. **Calculation Precision**: Uses Python's float (64-bit) for calculations, sufficient for accounting precision
2. **Rounding**: Display values rounded to 2 decimal places, calculations use full precision
3. **Excel Export**: Uses openpyxl library for native Excel files (not CSV)
4. **No Database**: All calculations are stateless - nothing is stored
5. **Educational Tool**: Shows all intermediate calculations for learning

## Troubleshooting

### Common Issues

1. **Port already in use**: Change port in app.py: `app.run(debug=True, port=5001)`
2. **Module not found**: Ensure virtual environment is activated and requirements installed
3. **Excel download fails**: Check openpyxl is installed: `pip install openpyxl`

### Debug Mode
Application runs in debug mode by default. For production:
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

## Future Enhancements

Potential additions while maintaining simplicity:
- Lease modification/remeasurement calculations
- Variable payment handling
- Multi-lease portfolio analysis
- IFRS 16 comparison mode
- Journal entry generation

## License

Built for educational and professional use. Based on public FASB ASC 842 standards.

## Support

For questions or issues, review the ASC 842 technical documentation in the Guidance tab or consult:
- FASB ASC 842 Codification
- Big 4 firm implementation guides
- Your organization's technical accounting team

---

**Remember**: This tool assists with calculations but doesn't replace professional judgment. Always review results and consult authoritative guidance for complex scenarios.

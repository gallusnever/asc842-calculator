// ASC 842 Calculator - Enhanced JavaScript

// Global variables
let currentResults = null;
let userAccepted = false;

// Check if user has accepted terms
document.addEventListener('DOMContentLoaded', () => {
    checkUserAcceptance();
    setupTermsForm();
});

// Tab switching
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        const tabName = button.getAttribute('data-tab');
        
        // Update active button
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        
        // Update active content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');
    });
});

// Form submission
document.getElementById('unified-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        // Basic lease terms
        lease_commencement_date: document.getElementById('lease_commencement_date').value,
        monthly_payment: parseFloat(document.getElementById('monthly_payment').value),
        lease_term_months: parseInt(document.getElementById('lease_term_months').value),
        payment_timing: document.getElementById('payment_timing').value,
        
        // Discount rate
        discount_rate: parseFloat(document.getElementById('discount_rate').value),
        use_treasury_rate: document.getElementById('use_treasury_rate').checked,
        
        // Optional classification inputs
        fair_value: document.getElementById('fair_value').value || null,
        asset_life_months: document.getElementById('asset_life_months').value || null,
        
        // Boolean classification tests
        has_transfer_title: document.getElementById('has_transfer_title').checked,
        has_bargain_purchase: document.getElementById('has_bargain_purchase').checked,
        is_specialized: document.getElementById('is_specialized').checked,
        
        // Initial recognition adjustments
        prepaid_rent: parseFloat(document.getElementById('prepaid_rent').value) || 0,
        initial_direct_costs: parseFloat(document.getElementById('initial_direct_costs').value) || 0,
        lease_incentives: parseFloat(document.getElementById('lease_incentives').value) || 0,
        
        // Reporting settings
        fiscal_year_end: document.getElementById('fiscal_year_end').value || '12/31'
    };
    
    try {
        const response = await fetch('/api/unified-calculation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentResults = data;
            displayResults(data);
            document.getElementById('results-container').style.display = 'block';
            document.querySelector('.download-section').style.display = 'block';
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Error calculating lease: ' + error.message);
    }
});

// Display results
function displayResults(data) {
    // Display classification results
    displayClassificationResults(data.classification);
    
    // Display initial recognition results
    displayRecognitionResults(data.initial_recognition);
    
    // Display amortization schedule
    displayAmortizationSchedule(data.amortization_schedule, data.classification.lease_type);
    
    // Display journal entries
    displayJournalEntries(data.journal_entries);
}

function displayClassificationResults(classification) {
    const container = document.getElementById('classification-results');
    
    let html = '<h3>Classification Results</h3>';
    html += `<div class="classification-result ${classification.lease_type.toLowerCase()}-lease">`;
    html += `<h4>${classification.lease_type} Lease</h4>`;
    
    // Show test results
    html += '<div class="test-results">';
    
    const tests = [
        { name: 'Transfer of Ownership', key: 'transfer_ownership' },
        { name: 'Bargain Purchase Option', key: 'bargain_purchase' },
        { name: 'Lease Term Test', key: 'lease_term' },
        { name: 'Present Value Test', key: 'present_value' },
        { name: 'Specialized Asset', key: 'specialized_asset' }
    ];
    
    tests.forEach(test => {
        const testData = classification.tests[test.key];
        const cssClass = testData.met ? 'test-met' : 'test-not-met';
        html += `<div class="test-item ${cssClass}">`;
        html += `<span class="test-name">${test.name}:</span> `;
        
        if (test.key === 'lease_term' && testData.value !== null) {
            html += `${(testData.value * 100).toFixed(1)}% of asset life`;
            if (testData.met) html += ` (≥ ${(testData.threshold * 100)}%)`;
        } else if (test.key === 'present_value' && testData.value !== null) {
            html += `${(testData.value * 100).toFixed(1)}% of fair value`;
            if (testData.met) html += ` (≥ ${(testData.threshold * 100)}%)`;
        } else {
            html += testData.value ? 'Yes' : 'No';
        }
        
        html += `<span class="test-status">${testData.met ? ' ✓' : ' ✗'}</span>`;
        html += '</div>';
    });
    
    html += '</div>';
    
    // Show calculations
    if (classification.calculations.pv_lease_payments) {
        html += '<div class="calculation-summary">';
        html += `<p>Present Value of Lease Payments: ${formatCurrency(classification.calculations.pv_lease_payments)}</p>`;
        html += '</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function displayRecognitionResults(recognition) {
    const container = document.getElementById('recognition-results');
    
    let html = '<h3>Initial Recognition</h3>';
    html += '<div class="recognition-details">';
    
    html += '<table class="recognition-table">';
    html += '<tr><td>Lease Liability:</td><td class="amount">' + formatCurrency(recognition.lease_liability) + '</td></tr>';
    
    if (recognition.components.prepaid_rent > 0) {
        html += '<tr><td>Add: Prepaid Rent:</td><td class="amount">' + formatCurrency(recognition.components.prepaid_rent) + '</td></tr>';
    }
    if (recognition.components.initial_direct_costs > 0) {
        html += '<tr><td>Add: Initial Direct Costs:</td><td class="amount">' + formatCurrency(recognition.components.initial_direct_costs) + '</td></tr>';
    }
    if (recognition.components.lease_incentives > 0) {
        html += '<tr><td>Less: Lease Incentives:</td><td class="amount">(' + formatCurrency(recognition.components.lease_incentives) + ')</td></tr>';
    }
    
    html += '<tr class="total-row"><td>ROU Asset:</td><td class="amount">' + formatCurrency(recognition.rou_asset) + '</td></tr>';
    html += '</table>';
    
    html += '</div>';
    container.innerHTML = html;
}

function displayAmortizationSchedule(schedule, leaseType) {
    const container = document.getElementById('amortization-results');
    
    let html = '<h3>Amortization Schedule</h3>';
    html += '<div class="schedule-table-container">';
    html += '<table class="amortization-table">';
    
    // Header
    html += '<thead><tr>';
    html += '<th rowspan="2">Month</th>';
    html += '<th colspan="3" class="rou-section">ROU Asset</th>';
    html += '<th colspan="4" class="liability-section">Lease Liability</th>';
    html += '<th rowspan="2">Total Expense</th>';
    html += '</tr>';
    html += '<tr>';
    // ROU Asset columns
    html += '<th class="rou-section">Beginning</th>';
    html += '<th class="rou-section">Amortization</th>';
    html += '<th class="rou-section">Ending</th>';
    // Liability columns
    html += '<th class="liability-section">Beginning</th>';
    html += '<th class="liability-section">Interest</th>';
    html += '<th class="liability-section">Principal</th>';
    html += '<th class="liability-section">Ending</th>';
    html += '</tr></thead>';
    
    html += '<tbody>';
    
    // Show first 12 months and last month
    const monthsToShow = schedule.length <= 13 ? schedule : [
        ...schedule.slice(0, 12),
        { month: '...', rou_asset: {}, liability: {}, total_expense: '...' },
        schedule[schedule.length - 1]
    ];
    
    monthsToShow.forEach(row => {
        if (row.month === '...') {
            html += '<tr class="ellipsis-row"><td colspan="9">...</td></tr>';
        } else {
            html += '<tr>';
            html += `<td>${row.month}</td>`;
            // ROU Asset
            html += `<td class="amount">${formatCurrency(row.rou_asset.beginning)}</td>`;
            html += `<td class="amount">${formatCurrency(row.rou_asset.amortization)}</td>`;
            html += `<td class="amount">${formatCurrency(row.rou_asset.ending)}</td>`;
            // Liability
            html += `<td class="amount">${formatCurrency(row.liability.beginning)}</td>`;
            html += `<td class="amount">${formatCurrency(row.liability.interest)}</td>`;
            html += `<td class="amount">${formatCurrency(row.liability.principal)}</td>`;
            html += `<td class="amount">${formatCurrency(row.liability.ending)}</td>`;
            // Total expense
            html += `<td class="amount">${formatCurrency(row.total_expense)}</td>`;
            html += '</tr>';
        }
    });
    
    html += '</tbody></table>';
    html += '</div>';
    
    container.innerHTML = html;
}

function displayJournalEntries(journalEntries) {
    const container = document.getElementById('journal-entries-results');
    
    let html = '<h3>Journal Entries</h3>';
    
    // Initial recognition entry
    html += '<div class="journal-entry-section">';
    html += '<h4>Initial Recognition</h4>';
    journalEntries.initial.forEach(entry => {
        html += formatJournalEntry(entry);
    });
    html += '</div>';
    
    // Periodic entries (show first 3 months)
    html += '<div class="journal-entry-section">';
    html += '<h4>Monthly Entries (First 3 Months Shown)</h4>';
    journalEntries.periodic.slice(0, 3).forEach(entry => {
        html += formatJournalEntry(entry);
    });
    
    if (journalEntries.periodic.length > 3) {
        html += '<p class="note">Additional entries continue for the full lease term. Download Excel for complete details.</p>';
    }
    html += '</div>';
    
    container.innerHTML = html;
}

function formatJournalEntry(entry) {
    let html = '<div class="journal-entry">';
    html += `<div class="entry-header">${entry.date} - ${entry.description}</div>`;
    html += '<table class="journal-table">';
    
    entry.entries.forEach(line => {
        html += '<tr>';
        html += `<td class="account">${line.account}</td>`;
        html += `<td class="debit">${line.debit > 0 ? formatCurrency(line.debit) : ''}</td>`;
        html += `<td class="credit">${line.credit > 0 ? formatCurrency(line.credit) : ''}</td>`;
        html += '</tr>';
    });
    
    html += '</table>';
    html += '</div>';
    return html;
}

// Treasury rate handling
document.getElementById('use_treasury_rate').addEventListener('change', async (e) => {
    const displayElement = document.getElementById('treasury_rate_display');
    const rateValueElement = document.getElementById('treasury_rate_value');
    
    if (e.target.checked) {
        // Load treasury rates
        try {
            const response = await fetch('/api/treasury-rates');
            const data = await response.json();
            
            if (data.success) {
                // Calculate appropriate rate based on lease term
                const leaseTerm = parseInt(document.getElementById('lease_term_months').value) || 60;
                const termYears = leaseTerm / 12;
                
                // Find closest treasury term
                const availableTerms = Object.keys(data.rates).map(t => parseFloat(t)).sort((a, b) => a - b);
                const closestTerm = availableTerms.reduce((prev, curr) => 
                    Math.abs(curr - termYears) < Math.abs(prev - termYears) ? curr : prev
                );
                
                const rate = data.rates[closestTerm];
                const termDisplay = closestTerm < 1 ? `${closestTerm * 12}M` : `${closestTerm}Y`;
                rateValueElement.innerHTML = `${(rate * 100).toFixed(3)}% (${termDisplay} Treasury)`;
                displayElement.style.display = 'block';
                
                // Update discount rate field
                document.getElementById('discount_rate').value = rate.toFixed(4);
                
                // Flash a warning to ensure user notices
                displayElement.style.animation = 'pulse 1s ease-in-out';
                setTimeout(() => {
                    displayElement.style.animation = '';
                }, 1000);
            }
        } catch (error) {
            console.error('Error loading treasury rates:', error);
        }
    } else {
        displayElement.style.display = 'none';
    }
});

// Load treasury rates on guidance tab
async function loadTreasuryRates() {
    try {
        const response = await fetch('/api/treasury-rates');
        const data = await response.json();
        
        if (data.success) {
            const container = document.getElementById('treasury-rates-display');
            let html = '<table class="rates-table">';
            html += '<thead><tr><th>Term</th><th>Rate</th></tr></thead>';
            html += '<tbody>';
            
            Object.entries(data.rates).forEach(([term, rate]) => {
                const termDisplay = parseFloat(term) < 1 ? `${parseFloat(term) * 12}M` : `${term}Y`;
                html += `<tr><td>${termDisplay}</td><td>${(rate * 100).toFixed(3)}%</td></tr>`;
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading treasury rates:', error);
    }
}

// Download complete analysis
async function downloadCompleteAnalysis() {
    if (!currentResults) return;
    
    try {
        const response = await fetch('/api/download-complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                results: currentResults,
                inputs: getFormInputs()
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ASC842_Analysis_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Error downloading analysis');
        }
    } catch (error) {
        alert('Error downloading analysis: ' + error.message);
    }
}

// Get form inputs for Excel download
function getFormInputs() {
    return {
        lease_commencement_date: document.getElementById('lease_commencement_date').value,
        monthly_payment: parseFloat(document.getElementById('monthly_payment').value),
        lease_term_months: parseInt(document.getElementById('lease_term_months').value),
        payment_timing: document.getElementById('payment_timing').value,
        discount_rate: parseFloat(document.getElementById('discount_rate').value),
        fair_value: document.getElementById('fair_value').value || null,
        asset_life_months: document.getElementById('asset_life_months').value || null,
        fiscal_year_end: document.getElementById('fiscal_year_end').value
    };
}

// Utility functions
function formatCurrency(amount) {
    if (amount === null || amount === undefined) return '';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatPercentage(value) {
    if (value === null || value === undefined) return '';
    return (value * 100).toFixed(2) + '%';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadTreasuryRates();
});

// Terms acceptance functions
async function checkUserAcceptance() {
    try {
        const response = await fetch('/api/check-acceptance', {
            method: 'GET',
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (data.accepted) {
            userAccepted = true;
            document.getElementById('termsModal').classList.add('hidden');
        } else {
            document.getElementById('termsModal').classList.remove('hidden');
            document.querySelector('.container').style.filter = 'blur(5px)';
            document.querySelector('.container').style.pointerEvents = 'none';
        }
    } catch (error) {
        // If check fails, show terms to be safe
        document.getElementById('termsModal').classList.remove('hidden');
        document.querySelector('.container').style.filter = 'blur(5px)';
        document.querySelector('.container').style.pointerEvents = 'none';
    }
}

function setupTermsForm() {
    const form = document.getElementById('termsForm');
    const checkbox = document.getElementById('acceptTerms');
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Enable/disable submit button based on checkbox
    checkbox.addEventListener('change', () => {
        submitBtn.disabled = !checkbox.checked;
    });
    
    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = {
            accepted: document.getElementById('acceptTerms').checked
        };
        
        try {
            const response = await fetch('/api/accept-terms', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData),
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success) {
                userAccepted = true;
                document.getElementById('termsModal').classList.add('hidden');
                document.querySelector('.container').style.filter = 'none';
                document.querySelector('.container').style.pointerEvents = 'auto';
            } else {
                alert('Error accepting terms. Please try again.');
            }
        } catch (error) {
            alert('Error accepting terms. Please try again.');
        }
    });
}

// Modify existing functions to check acceptance
const originalSubmit = document.getElementById('unified-form').addEventListener;
document.getElementById('unified-form').addEventListener = function(event, handler) {
    if (event === 'submit') {
        const wrappedHandler = async function(e) {
            if (!userAccepted) {
                e.preventDefault();
                alert('Please accept the terms of use before using this calculator.');
                return;
            }
            return handler.call(this, e);
        };
        return originalSubmit.call(this, event, wrappedHandler);
    }
    return originalSubmit.call(this, event, handler);
};
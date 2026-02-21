const API_BASE_URL = 'http://localhost:8000';

const form = document.getElementById('analysisForm');
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const resultsContainer = document.getElementById('resultsContainer');
const submitBtn = document.getElementById('submitBtn');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const propertyReference = document.getElementById('propertyReference').value;
    const budget = parseFloat(document.getElementById('budget').value);
    
    const improvementCheckboxes = document.querySelectorAll('input[name="improvements"]:checked');
    const desiredImprovements = Array.from(improvementCheckboxes).map(cb => cb.value);
    
    if (desiredImprovements.length === 0) {
        showError('Please select at least one improvement type');
        return;
    }
    
    const requestData = {
        property_reference: propertyReference,
        budget: budget,
        desired_improvements: desiredImprovements
    };
    
    await analyzeProperty(requestData);
});

async function analyzeProperty(data) {
    hideAll();
    loadingState.style.display = 'block';
    submitBtn.disabled = true;
    
    // Construct the payload to match your AddressAnalysisRequest model
    const payload = {
        address_query: data.property_reference, // Use the address entered in the UPRN box
        budget: data.budget,
        desired_improvements: data.desired_improvements
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/property/analyze-by-address`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload) // Send payload as JSON body
        });
        
        if (!response.ok) {
            const error = await response.json();
            // This handles the [object Object] error by converting the error detail to a string
            throw new Error(typeof error.detail === 'object' ? JSON.stringify(error.detail) : error.detail);
        }
        
        const results = await response.json();
        displayResults(results);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to analyze property.');
    } finally {
        loadingState.style.display = 'none';
        submitBtn.disabled = false;
    }
}

function displayResults(data) {
    hideAll();
    
    // Summary section
    const summarySection = document.getElementById('summarySection');
    summarySection.innerHTML = `<p><strong>Summary:</strong> ${data.summary}</p>`;
    
    // Stats grid
    const statsGrid = document.getElementById('statsGrid');
    const withinBudget = data.total_cost <= data.budget;
    
    statsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">£${data.total_cost.toLocaleString()}</div>
            <div class="stat-label">Total Cost</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${data.total_roi_percent.toFixed(1)}%</div>
            <div class="stat-label">Total ROI</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">£${data.total_value_increase.toLocaleString()}</div>
            <div class="stat-label">Value Increase</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${withinBudget ? '✓ Yes' : '✗ No'}</div>
            <div class="stat-label">Within Budget</div>
        </div>
    `;
    
    // Improvements section (Tabbed Interface)
    const improvementsSection = document.getElementById('improvementsSection');
    improvementsSection.innerHTML = '<h3 style="margin-bottom: 20px;">Improvement Analysis</h3>';
    
    // Create containers for the Tabs and the Content
    const tabsNav = document.createElement('div');
    tabsNav.className = 'tabs-nav';
    
    const tabsContent = document.createElement('div');
    tabsContent.className = 'tabs-content';
    
    data.improvements.forEach((improvement, index) => {
        const isFirst = index === 0;
        const prettyName = improvement.improvement_type.replace('_', ' ');
        
        // 1. Create Tab Button
        const tabBtn = document.createElement('button');
        tabBtn.className = `tab-btn ${isFirst ? 'active' : ''}`;
        tabBtn.textContent = prettyName;
        tabsNav.appendChild(tabBtn);
        
        // 2. Create Tab Content
        const tabPane = document.createElement('div');
        tabPane.className = `tab-pane ${isFirst ? 'active' : ''}`;
        
        const examplesHTML = improvement.examples && improvement.examples.length > 0 
            ? `
                <div class="examples-section">
                    <h4>Recent Approved Examples:</h4>
                    ${improvement.examples.slice(0, 3).map(example => `
                        <div class="example-item">
                            <span class="example-ref">${example.planning_reference}</span>
                            ${example.decision_time_days ? `<span> - Approved in ${example.decision_time_days} days</span>` : ''}
                            <br>
                            <span style="color: #666;">${example.proposal.substring(0, 100)}${example.proposal.length > 100 ? '...' : ''}</span>
                        </div>
                    `).join('')}
                </div>
            `
            : '<div class="examples-section"><p style="color: #999;">No recent examples found</p></div>';
        
        tabPane.innerHTML = `
            <div class="improvement-item">
                <div class="improvement-header">
                    <div class="improvement-title">${prettyName}</div>
                    <div class="feasibility-badge feasibility-${improvement.feasibility}">
                        ${improvement.feasibility} FEASIBILITY
                    </div>
                </div>
                <div class="improvement-details">
                    <div class="detail-item">
                        <div class="detail-label">Estimated Cost</div>
                        <div class="detail-value">£${improvement.estimated_cost.toLocaleString()}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">ROI</div>
                        <div class="detail-value">${improvement.estimated_roi_percent.toFixed(1)}%</div>
                    </div>
                    <div class="detail-item highlight-box">
                        <div class="detail-label">Value Increase</div>
                        <div class="detail-value">£${improvement.green_premium_value.toLocaleString()}</div>
                        ${improvement.value_explanation ? `<div class="detail-explanation">${improvement.value_explanation}</div>` : ''}
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Approved Examples</div>
                        <div class="detail-value">${improvement.approved_examples}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Avg. Approval Time</div>
                        <div class="detail-value">${improvement.average_time_days ? Math.round(improvement.average_time_days) + ' days' : 'N/A'}</div>
                    </div>
                </div>
                ${examplesHTML}
            </div>
        `;
        tabsContent.appendChild(tabPane);
        
        // 3. Add Click Event to Switch Tabs
        tabBtn.addEventListener('click', () => {
            // Remove active class from all tabs and panes
            Array.from(tabsNav.children).forEach(btn => btn.classList.remove('active'));
            Array.from(tabsContent.children).forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding pane
            tabBtn.classList.add('active');
            tabPane.classList.add('active');
        });
    });
    
    // Append the nav and content to the DOM
    improvementsSection.appendChild(tabsNav);
    improvementsSection.appendChild(tabsContent);
    
    resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function showError(message) {
    hideAll();
    errorState.style.display = 'block';
    document.querySelector('.error-message').textContent = message;
}

function hideAll() {
    loadingState.style.display = 'none';
    errorState.style.display = 'none';
    resultsContainer.style.display = 'none';
}

// Check API health on load
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) {
            console.warn('API health check failed');
        }
    } catch (error) {
        console.warn('Could not connect to API:', error);
    }
}

checkHealth();

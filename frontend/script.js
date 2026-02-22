const API_BASE_URL = 'http://localhost:8000';

let MAPBOX_TOKEN = "";
let mapInstances = {};

async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/config`);
        const data = await res.json();
        MAPBOX_TOKEN = data.mapboxToken;
    } catch (err) {
        console.error("Failed to load Mapbox token:", err);
    }
}

loadConfig();

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

// Render map and ensure it fills container and all markers appear
function renderMap(containerId, centerLat, centerLng, markers = []) {
    if (mapInstances[containerId]) mapInstances[containerId].remove();

    const oldCard = document.getElementById(containerId + "Card");
    if (oldCard) oldCard.remove();

    const mapCard = document.createElement('div');
    mapCard.className = 'card';
    mapCard.id = containerId + "Card";
    mapCard.style.marginTop = '20px';
    mapCard.innerHTML = `<div id="${containerId}" style="height:400px;width:100%;border-radius:8px;"></div>`;
    resultsContainer.appendChild(mapCard);

    mapboxgl.accessToken = MAPBOX_TOKEN;
    const map = new mapboxgl.Map({
        container: containerId,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [centerLng, centerLat],
        zoom: 15
    });

    markers.forEach(marker => {
        if (marker.lat != null && marker.lng != null) {
            new mapboxgl.Marker({ color: marker.color || '#e63946' })
                .setLngLat([marker.lng, marker.lat])
                .addTo(map);

            if (marker.label) {
                new mapboxgl.Popup({ offset: 25 })
                    .setLngLat([marker.lng, marker.lat])
                    .setHTML(`<strong>${marker.label}</strong>`)
                    .addTo(map);
            }
        }
    });

    // Save map instance
    mapInstances[containerId] = map;

    // Force resize after container becomes visible
    setTimeout(() => map.resize(), 100);
}
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


    // Map
    // Start with main property
    const markers = [
        {
            lat: data.location.latitude,
            lng: data.location.longitude,
            label: `Current Property: ${data.property_reference}`,
            color: '#e63946'
        }
    ];

    // Loop through improvements and their examples (if they have lat/lng)
    data.improvements.forEach(imp => {
        imp.examples.forEach(example => {
            if (example.latitude && example.longitude) {
                markers.push({
                    lat: example.latitude,
                    lng: example.longitude,
                    label: `${example.planning_reference}: ${imp.improvement_type}`,
                    color: '#457b9d' // different color for examples
                });
            }
        });
    });

    // Render map with all markers, centered on main property
    renderMap("propertyMap", data.location.latitude, data.location.longitude, markers);

    const EPC_SETTINGS = {
        colors: {
            current: '#2b2d42',
            predicted: '#8d99ae',
            goal: '#edf2f4',
            belowGoal: '#fbeaec', // fallback for bands below goal
            belowGoalText: '#7a222b',
            goalText: '#000',      // text on goal band
            predictedText: '#fff',
            currentText: '#fff',
        },
        epcOrder: ["G","F","E","D","C","B","A"],
        goalBand: "C",
        goalTextMuted: "Necessary EPC C by 2030"
    };

    if (data.energy_compliance) {
        const compliance = data.energy_compliance;

        const oldCard = document.getElementById('epcCard');
        if (oldCard) oldCard.remove();

        const epcCard = document.createElement('div');
        epcCard.id = 'epcCard';
        epcCard.className = 'epc-card';

        const title = document.createElement('h3');
        title.textContent = "Energy Compliance (EPC 2030 Target)";
        epcCard.appendChild(title);

        const mutedText = document.createElement('p');
        mutedText.className = 'text-muted';
        mutedText.style.fontSize = '0.85em';
        mutedText.style.color = '#5B6B45';
        mutedText.style.marginBottom = '8px';
        mutedText.textContent = EPC_SETTINGS.goalTextMuted;

        epcCard.appendChild(mutedText);

        const epcBar = document.createElement('div');
        epcBar.className = 'epc-bar-container';

        const currentIndex = EPC_SETTINGS.epcOrder.indexOf(compliance.current_epc);
        const projectedIndex = EPC_SETTINGS.epcOrder.indexOf(compliance.projected_epc);
        const goalIndex = EPC_SETTINGS.epcOrder.indexOf(EPC_SETTINGS.goalBand);

        EPC_SETTINGS.epcOrder.forEach((band, i) => {
            const segment = document.createElement('div');
            segment.className = 'epc-segment';
            segment.textContent = band;

            // Assign colors dynamically
            if (i <= currentIndex) {
                segment.style.backgroundColor = EPC_SETTINGS.colors.current;
                segment.style.color = EPC_SETTINGS.colors.currentText;
                segment.title = `${band} (Current)`;
            } else if (i <= projectedIndex) {
                segment.style.backgroundColor = EPC_SETTINGS.colors.predicted;
                segment.style.color = EPC_SETTINGS.colors.predictedText;
                segment.title = `${band} (Predicted)`;
            } else if (i <= goalIndex) {
                segment.style.backgroundColor = EPC_SETTINGS.colors.goal;
                segment.style.color = EPC_SETTINGS.colors.goalText;
                segment.title = `${band} (Goal)`;
            } else {
                segment.style.backgroundColor = EPC_SETTINGS.colors.belowGoal;
                segment.style.color = EPC_SETTINGS.colors.belowGoalText;
                segment.title = band;
            }

            epcBar.appendChild(segment);    
        });

        epcCard.appendChild(epcBar);

        // Legend dynamically
        const legend = document.createElement('div');
        legend.className = 'epc-legend';

        const legendItems = [
            { label: 'Current', color: EPC_SETTINGS.colors.current, textColor: EPC_SETTINGS.colors.currentText },
            { label: 'Predicted', color: EPC_SETTINGS.colors.predicted, textColor: EPC_SETTINGS.colors.predictedText },
            { label: `Goal`, color: EPC_SETTINGS.colors.belowGoal, textColor: EPC_SETTINGS.colors.goalText }
        ];

        legendItems.forEach(item => {
            const span = document.createElement('span');
            const box = document.createElement('div');
            box.className = 'box';
            box.style.backgroundColor = item.color;
            if(item.textColor) box.style.color = item.textColor;
            span.appendChild(box);
            const text = document.createTextNode(item.label);
            span.appendChild(text);
            legend.appendChild(span);
        });

        epcCard.appendChild(legend);

        resultsContainer.appendChild(epcCard);
    }
        
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

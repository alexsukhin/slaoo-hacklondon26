const API_BASE_URL = 'http://localhost:8000';

let MAPBOX_TOKEN = "";
let mapInstances = {};

// Load Mapbox token from backend
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

// Form elements
const form = document.getElementById('analysisForm');
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const submitBtn = document.getElementById('submitBtn');
const resultsContainer = document.getElementById('resultsContainer');

// Normalize EPC band safely
function normalizeEpcBand(band) {
    if (!band) return "D";
    return band.toUpperCase().trim();
}
// Navigation Logic
const navButtons = document.querySelectorAll('.nav-btn');
const contentSections = document.querySelectorAll('.content-section');

function switchTab(targetId) {
    // Hide all sections and remove active classes from buttons
    contentSections.forEach(section => section.classList.remove('active'));
    navButtons.forEach(btn => btn.classList.remove('active'));

    // Show target section and highlight corresponding button
    document.getElementById(targetId).classList.add('active');
    const activeBtn = document.querySelector(`.nav-btn[data-target="${targetId}"]`);
    if(activeBtn) activeBtn.classList.add('active');

    // VERY IMPORTANT: Mapbox requires a resize event if it was rendered while hidden
    if (targetId === 'mapSection') {
        Object.values(mapInstances).forEach(map => {
            setTimeout(() => map.resize(), 50);
        });
    }
}

navButtons.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.target));
});

// Map marker color by EPC
function getEpcColor(band) {
    const epcColors = {
        A: '#1a9641',
        B: '#4daf4a',
        C: '#a6d96a',
        D: '#ffffbf',
        E: '#fdae61',
        F: '#f46d43',
        G: '#d73027'
    };
    return epcColors[normalizeEpcBand(band)] || '#457b9d';
}

// Render map targeting the specific map section
// Render map targeting the specific map section
function renderMap(containerId, centerLat, centerLng, markers = []) {
    const mapSection = document.getElementById('mapSection');
    
    if (mapInstances[containerId]) mapInstances[containerId].remove();

    // Clean up old instances of this specific map card and its legend
    const oldCard = document.getElementById(containerId + "Card");
    if (oldCard) oldCard.remove();
    const oldLegend = document.getElementById(containerId + "Legend");
    if (oldLegend) oldLegend.remove();

    // 1. Create Map Card
    const mapCard = document.createElement('div');
    mapCard.className = 'card';
    mapCard.id = containerId + "Card";
    mapCard.innerHTML = `<h2 style="margin-bottom:20px;">Local Planning Examples</h2><div id="${containerId}" style="height:500px;width:100%;border-radius:8px;"></div>`;
    mapSection.appendChild(mapCard);

    // 2. Create Map Legend Card
    const legendCard = document.createElement('div');
    legendCard.className = 'card';
    legendCard.id = containerId + "Legend";
    legendCard.style.marginTop = '15px';
    
    const epcColors = {
        A: '#1a9641', B: '#4daf4a', C: '#a6d96a', D: '#ffffbf',
        E: '#fdae61', F: '#f46d43', G: '#d73027'
    };

    let legendHTML = `<h4 style="margin-bottom:15px;">Map Key: EPC Ratings</h4><div style="display: flex; flex-wrap: wrap; gap: 15px;">`;
    Object.entries(epcColors).forEach(([band, color]) => {
        legendHTML += `
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: ${color}; border: 1px solid #ccc;"></div>
                <span style="font-size: 0.85rem; font-weight: 600;">Band ${band}</span>
            </div>`;
    });
    legendHTML += `</div>`;
    legendCard.innerHTML = legendHTML;
    mapSection.appendChild(legendCard);

    // 3. Initialize Mapbox
    mapboxgl.accessToken = MAPBOX_TOKEN;
    const map = new mapboxgl.Map({
        container: containerId,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [centerLng, centerLat],
        zoom: 15
    });

    map.addControl(new mapboxgl.NavigationControl(), 'top-right');

    markers.forEach(marker => {
        if (marker.lat != null && marker.lng != null) {
            const el = document.createElement('div');
            const size = marker.size || 14;
            el.style.width = size + 'px';
            el.style.height = size + 'px';
            el.style.borderRadius = '50%';
            el.style.backgroundColor = getEpcColor(marker.epc);
            el.style.border = '1.5px solid white';
            el.style.boxShadow = '0 0 6px rgba(0,0,0,0.4)';
            el.style.cursor = 'pointer';

            const markerInstance = new mapboxgl.Marker(el).setLngLat([marker.lng, marker.lat]);

            if (marker.label) {
                const popup = new mapboxgl.Popup({ offset: 12 }).setHTML(marker.label);
                markerInstance.setPopup(popup);
            }

            markerInstance.addTo(map);
        }
    });

    mapInstances[containerId] = map;
    setTimeout(() => map.resize(), 100);
}
// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const propertyReference = document.getElementById('propertyReference').value;
    const budget = parseFloat(document.getElementById('budget').value);

    const improvementCheckboxes = document.querySelectorAll('input[name="improvements"]:checked');
    const desiredImprovements = Array.from(improvementCheckboxes).map(cb => cb.value.toLowerCase());

    if (desiredImprovements.length === 0) {
        showError('Please select at least one improvement type');
        return;
    }

    const addressQuery = document.getElementById('propertyAddress')?.value || propertyReference;

    const requestData = {
        address_query: addressQuery,
        budget: budget,
        desired_improvements: desiredImprovements
    };

    await analyzeProperty(requestData);
});


async function analyzeProperty(data) {
    hideGlobalStates();
    // Hide all main content while loading
    contentSections.forEach(section => section.classList.remove('active'));
    loadingState.style.display = 'block';
    submitBtn.disabled = true;
    
    const payload = {
        address_query: data.address_query, 
        budget: data.budget,
        desired_improvements: data.desired_improvements
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/property/analyze-by-address`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload) 
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(typeof error.detail === 'object' ? JSON.stringify(error.detail) : error.detail);
        }

        const results = await response.json();
        displayResults(results);
        
        // Show navigation options and switch to Overview
        document.getElementById('resultsNav').style.display = 'block';
        switchTab('overviewSection');
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Failed to analyze property.');
        switchTab('formSection'); // Go back to form if it failed
    } finally {
        loadingState.style.display = 'none';
        submitBtn.disabled = false;
    }
}

// Display results
// Display results
function displayResults(data) {
    hideGlobalStates();

    // Summary
    const summarySection = document.getElementById('summarySection');
    summarySection.innerHTML = `<p><strong>Summary:</strong> ${data.summary}</p>`;

    // Stats
    const statsGrid = document.getElementById('statsGrid');
    const withinBudget = data.total_cost <= data.budget;
    const treesEquivalent = Math.round(data.total_co2_savings / 21);
    
    statsGrid.innerHTML = `
        <div class="stat-card" style="border-color: var(--primary-green); background-color: var(--status-high-bg);">
            <div class="stat-value" style="color: var(--primary-green);">🌱 ${data.total_co2_savings.toLocaleString()} kg</div>
            <div class="stat-label">Annual CO₂ Reduction</div>
            <div style="font-size: 0.8rem; margin-top: 8px; color: var(--text-muted);">
                Equivalent to planting <strong>${treesEquivalent} trees</strong>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-value">£${data.total_cost.toLocaleString()}</div>
            <div class="stat-label">Green Investment</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">£${(Math.round(data.total_value_increase / 100) * 100).toLocaleString()}</div>
            <div class="stat-label">Green Premium</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${withinBudget ? '✓ Yes' : '✗ No'}</div>
            <div class="stat-label">Within Budget</div>
        </div>
    `;

    // Improvements tabs
    const improvementsSection = document.getElementById('improvementsSection');
    improvementsSection.innerHTML = '<h3 style="margin-bottom: 20px;">Improvement Analysis</h3>';
    
    const tabsNav = document.createElement('div');
    tabsNav.className = 'tabs-nav';
    const tabsContent = document.createElement('div');
    tabsContent.className = 'tabs-content';
    
    data.improvements.forEach((improvement, index) => {
        const isFirst = index === 0;
        const prettyName = improvement.improvement_type.replace('_', ' ');
        
        const tabBtn = document.createElement('button');
        tabBtn.className = `tab-btn ${isFirst ? 'active' : ''}`;
        tabBtn.textContent = prettyName;
        tabsNav.appendChild(tabBtn);
        
        const tabPane = document.createElement('div');
        tabPane.className = `tab-pane ${isFirst ? 'active' : ''}`;

        const examplesHTML = improvement.examples && improvement.examples.length > 0
            ? `<div class="examples-section"><h4>Recent Approved Examples:</h4>
               ${improvement.examples.slice(0,3).map(ex => `
                 <div class="example-item">
                   <span class="example-ref">${ex.planning_reference}</span>
                   ${ex.decision_time_days ? ` - ${ex.decision_time_days} days` : ''}
                   <br><span style="color:#666;">${ex.proposal.substring(0,100)}${ex.proposal.length>100?'...':''}</span>
                 </div>`).join('')}</div>`
            : '<div class="examples-section"><p style="color:#999;">No recent examples found</p></div>';

        const rawFeasibility = improvement.feasibility || "LOW";
        
        // Bulletproof way to extract the base rating. If it doesn't say HIGH or MEDIUM, it defaults to LOW.
        let baseFeasibility = "LOW";
        if (rawFeasibility.toUpperCase().includes("HIGH")) baseFeasibility = "HIGH";
        else if (rawFeasibility.toUpperCase().includes("MEDIUM")) baseFeasibility = "MEDIUM";
        
        const isConservation = rawFeasibility.includes('Conservation Area');
        
        // Create a prominent warning banner if it's in a conservation area
        const warningHTML = isConservation ? `
            <div class="conservation-warning">
                <span style="font-size: 1.2rem;">🏛️</span>
                <div>
                    <strong>Conservation Area Constraints Apply</strong><br>
                    ${rawFeasibility.replace(baseFeasibility + ' - ', '')}
                </div>
            </div>
        ` : '';
        // ------------------------------------

        tabPane.innerHTML = `
            <div class="improvement-item">
                <div class="improvement-header">
                    <div class="improvement-title">${prettyName}</div>
                    <div class="feasibility-badge feasibility-${baseFeasibility}">${baseFeasibility} FEASIBILITY</div>
                </div>
                
                ${warningHTML}

                <div class="improvement-details">
                    <div class="detail-item">
                        <div class="detail-label">Green Investment</div>
                        <div class="detail-value">£${improvement.estimated_cost.toLocaleString()}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Energy Savings</div>
                        <div class="detail-value">${improvement.kwh_savings.toLocaleString()} kWh/yr</div>
                    </div>
                    <div class="detail-item highlight-box">
                        <div class="detail-label">Green Premium</div>
                        <div class="detail-value">£${(Math.round(improvement.green_premium_value / 100) * 100).toLocaleString()}</div>
                        ${improvement.value_explanation ? `<div class="detail-explanation">${improvement.value_explanation}</div>` : ''}
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">CO₂ Reduction</div>
                        <div class="detail-value">${improvement.co2_savings_kg.toLocaleString()} kg/yr</div>
                    </div>
                </div>
                ${examplesHTML}
            </div>
        `;

        tabsContent.appendChild(tabPane);
        
        tabBtn.addEventListener('click', () => {
            Array.from(tabsNav.children).forEach(btn => btn.classList.remove('active'));
            Array.from(tabsContent.children).forEach(pane => pane.classList.remove('active'));
            
            tabBtn.classList.add('active');
            tabPane.classList.add('active');
        });
    });
    
    improvementsSection.appendChild(tabsNav);
    improvementsSection.appendChild(tabsContent);

    // Map logic remains identical
    const markers = [{
        lat: data.location.latitude,
        lng: data.location.longitude,
        label: `Current Property: ${data.property_reference}`,
        epc: data.energy_compliance.current_energy_rating,
        size: 16
    }];

    data.improvements.forEach(imp => {
        imp.examples.forEach(ex => {
            if(ex.latitude && ex.longitude){
                markers.push({
                    lat: ex.latitude,
                    lng: ex.longitude,
                    label: `<strong>${ex.planning_reference}</strong><br>${imp.improvement_type}<br>EPC: ${normalizeEpcBand(ex.current_energy_rating) || 'Unknown'}`,
                    epc: normalizeEpcBand(ex.current_energy_rating),
                    size: 12,
                });
            }
        });
    });

    renderMap("propertyMap", data.location.latitude, data.location.longitude, markers);

    // EPC Settings & Logic
    const EPC_SETTINGS = {
        colors: {
            current: '#2b2d42', predicted: '#8d99ae', goal: '#edf2f4',
            belowGoal: '#fbeaec', belowGoalText: '#7a222b',
            goalText: '#000', predictedText: '#fff', currentText: '#fff',
        },
        epcOrder: ["G","F","E","D","C","B","A"],
        goalBand: "C",
        goalTextMuted: "Necessary EPC C by 2030"
    };

    if (data.energy_compliance) {
        const compliance = data.energy_compliance;
        const epcSection = document.getElementById('epcSection');
        epcSection.innerHTML = '';

        const epcCard = document.createElement('div');
        epcCard.id = 'epcCard';
        epcCard.className = 'card epc-card';

        const title = document.createElement('h2');
        title.textContent = "Energy & Environmental Compliance";
        epcCard.appendChild(title);

        const mutedText = document.createElement('p');
        mutedText.className = 'text-muted';
        mutedText.style.fontSize = '0.95rem';
        mutedText.style.color = '#5B6B45';
        mutedText.style.marginBottom = '20px';
        mutedText.textContent = EPC_SETTINGS.goalTextMuted;
        epcCard.appendChild(mutedText);

        const epcBar = document.createElement('div');
        epcBar.className = 'epc-bar-container';

        const currentIndex = EPC_SETTINGS.epcOrder.indexOf(compliance.current_energy_rating);
        const projectedIndex = EPC_SETTINGS.epcOrder.indexOf(compliance.projected_epc);
        const goalIndex = EPC_SETTINGS.epcOrder.indexOf(EPC_SETTINGS.goalBand);

        EPC_SETTINGS.epcOrder.forEach((band, i) => {
            const segment = document.createElement('div');
            segment.className = 'epc-segment';
            segment.textContent = band;

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

        const legend = document.createElement('div');
        legend.className = 'epc-legend';
        legend.style.marginTop = '20px';

        const legendItems = [
            { label: 'Current Rating', color: EPC_SETTINGS.colors.current, textColor: EPC_SETTINGS.colors.currentText },
            { label: 'Predicted Output', color: EPC_SETTINGS.colors.predicted, textColor: EPC_SETTINGS.colors.predictedText },
            { label: 'Target Minimum', color: EPC_SETTINGS.colors.belowGoal, textColor: EPC_SETTINGS.colors.goalText }
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
        
        // Inject Real Carbon Data if available
        if (compliance.current_co2_emissions) {
            const carbonData = document.createElement('div');
            carbonData.style.marginTop = '25px';
            carbonData.style.paddingTop = '20px';
            carbonData.style.borderTop = '1px dashed var(--border-color)';
            carbonData.innerHTML = `
                <h4 style="margin-bottom: 12px; font-size: 1rem;">Current Property Footprint (EPC Data)</h4>
                <div style="display: flex; gap: 20px;">
                    <div><span style="color: var(--text-muted); font-size: 0.85rem;">Current Emissions:</span> <br><strong>${compliance.current_co2_emissions} tonnes/yr</strong></div>
                    <div><span style="color: var(--text-muted); font-size: 0.85rem;">Potential Emissions:</span> <br><strong>${compliance.potential_co2_emissions} tonnes/yr</strong></div>
                    ${compliance.current_energy_consumption ? `<div><span style="color: var(--text-muted); font-size: 0.85rem;">Energy Consumption:</span> <br><strong>${compliance.current_energy_consumption} kWh/m²/yr</strong></div>` : ''}
                </div>
            `;
            epcCard.appendChild(carbonData);
        }

        epcCard.appendChild(legend);
        epcSection.appendChild(epcCard);
    }
}
function showError(message) {
    hideGlobalStates();
    errorState.style.display = 'block';
    document.querySelector('.error-message').textContent = message;
}

function hideGlobalStates() {
    loadingState.style.display = 'none';
    errorState.style.display = 'none';
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) console.warn('API health check failed');
    } catch (error) {
        console.warn('Could not connect to API:', error);
    }
}
checkHealth();
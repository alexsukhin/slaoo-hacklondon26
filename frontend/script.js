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
const resultsContainer = document.getElementById('resultsContainer');
const submitBtn = document.getElementById('submitBtn');

// Normalize EPC band safely
function normalizeEpcBand(band) {
    if (!band) return "D";
    return band.toUpperCase().trim();
}

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

// Render Mapbox map with markers
function renderMap(containerId, centerLat, centerLng, markers = []) {
    if (mapInstances[containerId]) mapInstances[containerId].remove();

    const oldCard = document.getElementById(containerId + "Card");
    if (oldCard) oldCard.remove();

    const mapCard = document.createElement('div');
    mapCard.className = 'card';
    mapCard.id = containerId + "Card";
    mapCard.style.marginTop = '20px';
    mapCard.innerHTML = `<div id="${containerId}" style="height:400px;width:100%;border-radius:8px;overflow:hidden;"></div>`;
    resultsContainer.appendChild(mapCard);

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

// Analyze property
async function analyzeProperty(data) {
    hideAll();
    loadingState.style.display = 'block';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/api/property/analyze-by-address`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
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

// Display results
function displayResults(data) {
    hideAll();
    resultsContainer.style.display = 'block';

    // Summary
    const summarySection = document.getElementById('summarySection');
    summarySection.innerHTML = `<p><strong>Summary:</strong> ${data.summary}</p>`;

    // Stats
    const statsGrid = document.getElementById('statsGrid');
    const withinBudget = data.total_cost <= data.budget;
    statsGrid.innerHTML = `
        <div class="stat-card"><div class="stat-value">£${data.total_cost.toLocaleString()}</div><div class="stat-label">Total Cost</div></div>
        <div class="stat-card"><div class="stat-value">${data.total_roi_percent.toFixed(1)}%</div><div class="stat-label">Total ROI</div></div>
        <div class="stat-card"><div class="stat-value">£${data.total_value_increase.toLocaleString()}</div><div class="stat-label">Value Increase</div></div>
        <div class="stat-card"><div class="stat-value">${withinBudget ? '✓ Yes' : '✗ No'}</div><div class="stat-label">Within Budget</div></div>
    `;

    // Improvements tabs
    const improvementsSection = document.getElementById('improvementsSection');
    improvementsSection.innerHTML = '<h3 style="margin-bottom:20px;">Improvement Analysis</h3>';
    const tabsNav = document.createElement('div'); tabsNav.className = 'tabs-nav';
    const tabsContent = document.createElement('div'); tabsContent.className = 'tabs-content';

    data.improvements.forEach((imp, idx) => {
        const tabBtn = document.createElement('button');
        tabBtn.className = `tab-btn ${idx === 0 ? 'active' : ''}`;
        tabBtn.textContent = imp.improvement_type.replace('_',' ');
        tabsNav.appendChild(tabBtn);

        const tabPane = document.createElement('div');
        tabPane.className = `tab-pane ${idx === 0 ? 'active' : ''}`;

        const examplesHTML = imp.examples && imp.examples.length > 0
            ? `<div class="examples-section"><h4>Recent Approved Examples:</h4>
               ${imp.examples.slice(0,3).map(ex => `
                 <div class="example-item">
                   <span class="example-ref">${ex.planning_reference}</span>
                   ${ex.decision_time_days ? ` - ${ex.decision_time_days} days` : ''}
                   <br><span style="color:#666;">${ex.proposal.substring(0,100)}${ex.proposal.length>100?'...':''}</span>
                 </div>`).join('')}</div>`
            : '<div class="examples-section"><p style="color:#999;">No recent examples found</p></div>';

        tabPane.innerHTML = `
            <div class="improvement-item">
                <div class="improvement-header">
                    <div class="improvement-title">${imp.improvement_type.replace('_',' ')}</div>
                    <div class="feasibility-badge feasibility-${imp.feasibility}">${imp.feasibility} FEASIBILITY</div>
                </div>
                <div class="improvement-details">
                    <div class="detail-item"><div class="detail-label">Estimated Cost</div><div class="detail-value">£${imp.estimated_cost.toLocaleString()}</div></div>
                    <div class="detail-item"><div class="detail-label">ROI</div><div class="detail-value">${imp.estimated_roi_percent.toFixed(1)}%</div></div>
                    <div class="detail-item highlight-box"><div class="detail-label">Value Increase</div><div class="detail-value">£${imp.green_premium_value.toLocaleString()}</div>${imp.value_explanation?`<div class="detail-explanation">${imp.value_explanation}</div>`:''}</div>
                    <div class="detail-item"><div class="detail-label">Approved Examples</div><div class="detail-value">${imp.approved_examples}</div></div>
                    <div class="detail-item"><div class="detail-label">Avg. Approval Time</div><div class="detail-value">${imp.average_time_days?Math.round(imp.average_time_days)+' days':'N/A'}</div></div>
                </div>
                ${examplesHTML}
            </div>
        `;

        tabsContent.appendChild(tabPane);

        tabBtn.addEventListener('click', () => {
            Array.from(tabsNav.children).forEach(b=>b.classList.remove('active'));
            Array.from(tabsContent.children).forEach(p=>p.classList.remove('active'));
            tabBtn.classList.add('active');
            tabPane.classList.add('active');
        });
    });

    improvementsSection.appendChild(tabsNav);
    improvementsSection.appendChild(tabsContent);

    // Map markers
    const markers = [{
        lat: data.location.latitude,
        lng: data.location.longitude,
        label: `Current Property: ${data.property_reference}`,
        epc: data.energy_compliance?.current_epc,
        size: 16
    }];
    data.improvements.forEach(imp => {
        imp.examples.forEach(ex => {
            if(ex.latitude && ex.longitude){
                markers.push({
                    lat: ex.latitude,
                    lng: ex.longitude,
                    label: `<strong>${ex.planning_reference}</strong><br>${imp.improvement_type}<br>EPC: ${normalizeEpcBand(ex.current_epc) || 'Unknown'}`,
                    epc: normalizeEpcBand(ex.current_energy_rating) || data.energy_compliance?.current_epc,
                    size: 12
                });
            }
        });
    });

    renderMap('propertyMap', data.location.latitude, data.location.longitude, markers);

    // EPC bar
    if(data.energy_compliance){
        const epcSettings = {
            colors:{current:'#2b2d42',predicted:'#8d99ae',goal:'#edf2f4',belowGoal:'#fbeaec'},
            epcOrder:["G","F","E","D","C","B","A"],
            goalBand:"C"
        };

        const oldCard = document.getElementById('epcCard'); if(oldCard) oldCard.remove();
        const epcCard = document.createElement('div'); epcCard.id='epcCard'; epcCard.className='epc-card';
        epcCard.innerHTML='<h3>Energy Compliance (EPC 2030 Target)</h3>';

        const epcBar = document.createElement('div'); epcBar.className='epc-bar-container';

        const currentEpc = normalizeEpcBand(data.energy_compliance.current_epc);
        const projectedEpc = normalizeEpcBand(data.energy_compliance.projected_epc);
        const goalIndex = epcSettings.epcOrder.indexOf(epcSettings.goalBand);

        epcSettings.epcOrder.forEach((band,i)=>{
            const seg = document.createElement('div'); seg.className='epc-segment'; seg.textContent=band;
            if(i <= epcSettings.epcOrder.indexOf(currentEpc)){ seg.style.backgroundColor=epcSettings.colors.current; seg.style.color='#fff'; }
            else if(i <= epcSettings.epcOrder.indexOf(projectedEpc)){ seg.style.backgroundColor=epcSettings.colors.predicted; seg.style.color='#fff'; }
            else if(i <= goalIndex){ seg.style.backgroundColor=epcSettings.colors.goal; seg.style.color='#000'; }
            else { seg.style.backgroundColor=epcSettings.colors.belowGoal; seg.style.color='#7a222b'; }
            epcBar.appendChild(seg);
        });

        epcCard.appendChild(epcBar);
        resultsContainer.appendChild(epcCard);
    }

    resultsContainer.scrollIntoView({behavior:'smooth', block:'nearest'});
}

// Error and hide helpers
function showError(msg){ hideAll(); errorState.style.display='block'; document.querySelector('.error-message').textContent=msg; }
function hideAll(){ loadingState.style.display='none'; errorState.style.display='none'; resultsContainer.style.display='none'; }
// Nodan Frontend Application
const API_BASE = window.location.port === '8000' ? '' : 'http://localhost:8000';

// State
let currentQuery = '';
let currentOffset = 0;
let currentLimit = 20;
let totalResults = 0;
let mapMarkers = [];
let map = null;

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const resultsList = document.getElementById('resultsList');
const loadingState = document.getElementById('loadingState');
const resultCount = document.getElementById('resultCount');
const pagination = document.getElementById('pagination');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const pageInfo = document.getElementById('pageInfo');
const mapCount = document.getElementById('mapCount');
const hostModal = document.getElementById('hostModal');
const closeModal = document.getElementById('closeModal');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadStats();
    setupEventListeners();
    updateTime();
    setInterval(updateTime, 1000);
});

// Initialize Leaflet Map
function initMap() {
    map = L.map('map', {
        center: [20, 0],
        zoom: 2,
        zoomControl: true,
        attributionControl: false
    });
    
    // Dark map tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(map);
    
    // Custom marker icon
    const greenIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="width: 10px; height: 10px; background: #00ff41; border-radius: 50%; box-shadow: 0 0 10px #00ff41;"></div>',
        iconSize: [10, 10],
        iconAnchor: [5, 5]
    });
    
    window.markerIcon = greenIcon;
}

// Setup Event Listeners
function setupEventListeners() {
    // Search on Enter
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Search button
    searchBtn.addEventListener('click', performSearch);
    
    // Quick filters
    document.querySelectorAll('.quick-filter').forEach(btn => {
        btn.addEventListener('click', () => {
            searchInput.value = btn.dataset.filter;
            performSearch();
        });
    });
    
    // Pagination
    prevBtn.addEventListener('click', () => {
        if (currentOffset > 0) {
            currentOffset -= currentLimit;
            performSearch(false);
        }
    });
    
    nextBtn.addEventListener('click', () => {
        if (currentOffset + currentLimit < totalResults) {
            currentOffset += currentLimit;
            performSearch(false);
        }
    });
    
    // Modal close
    closeModal.addEventListener('click', closeHostModal);
    hostModal.addEventListener('click', (e) => {
        if (e.target === hostModal) closeHostModal();
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeHostModal();
        if (e.key === '/' && !e.target.matches('input')) {
            e.preventDefault();
            searchInput.focus();
        }
    });
}

// Perform Search
async function performSearch(resetOffset = true) {
    const query = searchInput.value.trim();
    
    if (resetOffset) {
        currentOffset = 0;
    }
    
    currentQuery = query;
    
    // Show loading
    resultsList.classList.add('hidden');
    loadingState.classList.remove('hidden');
    pagination.classList.add('hidden');
    
    try {
        const params = new URLSearchParams({
            q: query,
            limit: currentLimit,
            offset: currentOffset
        });
        
        const response = await fetch(`${API_BASE}/api/search?${params}`);
        
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        
        displayResults(data);
        updateMap(data.results);
        
    } catch (error) {
        console.error('Search error:', error);
        resultsList.innerHTML = `
            <div class="p-8 text-center text-hacker-red">
                <p class="text-sm">ERROR: ${error.message}</p>
            </div>
        `;
        resultsList.classList.remove('hidden');
    } finally {
        loadingState.classList.add('hidden');
    }
}

// Display Search Results
function displayResults(data) {
    totalResults = data.total;
    const results = data.results;
    
    resultCount.textContent = `${totalResults} devices found`;
    
    if (results.length === 0) {
        resultsList.innerHTML = `
            <div class="p-8 text-center text-hacker-green/30">
                <p class="text-sm">No results found</p>
            </div>
        `;
        resultsList.classList.remove('hidden');
        pagination.classList.add('hidden');
        return;
    }
    
    resultsList.innerHTML = results.map((result, index) => {
        const serviceClass = getServiceClass(result.service);
        const portBadge = result.port ? `<span class="service-badge ${serviceClass}">${result.port}</span>` : '';
        
        return `
            <div class="result-card p-4 cursor-pointer" data-ip="${result.ip}" onclick="showHostDetails('${result.ip}')">
                <div class="flex items-start justify-between gap-4">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-hacker-green font-bold">${result.ip}</span>
                            ${portBadge}
                            <span class="text-xs text-hacker-cyan/50">${result.service || 'unknown'}</span>
                        </div>
                        ${result.banner ? `<p class="text-xs text-gray-500 truncate">${escapeHtml(result.banner)}</p>` : ''}
                        <div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
                            ${result.country ? `<span>${getCountryFlag(result.country)} ${result.country}</span>` : ''}
                            ${result.city ? `<span>${result.city}</span>` : ''}
                            ${result.org ? `<span>${escapeHtml(result.org)}</span>` : ''}
                        </div>
                    </div>
                    <div class="text-xs text-gray-600">
                        ${formatTimestamp(result.timestamp)}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    resultsList.classList.remove('hidden');
    
    // Update pagination
    updatePagination();
}

// Update Pagination
function updatePagination() {
    const currentPage = Math.floor(currentOffset / currentLimit) + 1;
    const totalPages = Math.ceil(totalResults / currentLimit);
    
    if (totalPages > 1) {
        pagination.classList.remove('hidden');
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        prevBtn.disabled = currentOffset === 0;
        nextBtn.disabled = currentOffset + currentLimit >= totalResults;
    } else {
        pagination.classList.add('hidden');
    }
}

// Update Map
function updateMap(results) {
    // Clear existing markers
    mapMarkers.forEach(marker => map.removeLayer(marker));
    mapMarkers = [];
    
    // Add markers for results with coordinates
    const mapResults = results.filter(r => r.latitude && r.longitude);
    
    mapCount.textContent = `${mapResults.length} nodes`;
    
    mapResults.forEach(result => {
        const marker = L.marker([result.latitude, result.longitude], {
            icon: window.markerIcon
        }).addTo(map);
        
        marker.bindPopup(`
            <div style="background: #0a0a0a; color: #00ff41; padding: 8px; min-width: 150px;">
                <strong>${result.ip}</strong><br>
                <span style="color: #888;">${result.service || 'unknown'}</span><br>
                <span style="color: #666; font-size: 11px;">${result.country || ''} ${result.city || ''}</span>
            </div>
        `, {
            className: 'dark-popup'
        });
        
        marker.on('click', () => showHostDetails(result.ip));
        
        mapMarkers.push(marker);
    });
    
    // Fit bounds if we have markers
    if (mapMarkers.length > 0) {
        const group = L.featureGroup(mapMarkers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Show Host Details Modal
async function showHostDetails(ip) {
    hostModal.classList.remove('hidden');
    hostModal.classList.add('flex');
    
    document.getElementById('modalIp').textContent = ip;
    document.getElementById('modalLocation').textContent = 'Loading...';
    document.getElementById('modalAsn').textContent = '...';
    document.getElementById('modalOrg').textContent = '...';
    document.getElementById('modalPorts').textContent = '...';
    document.getElementById('modalLastScan').textContent = '...';
    document.getElementById('modalPortsTable').innerHTML = '<tr><td colspan="4" class="text-center py-4 text-gray-500">Loading...</td></tr>';
    
    try {
        const response = await fetch(`${API_BASE}/api/host/${ip}`);
        
        if (!response.ok) throw new Error('Host not found');
        
        const data = await response.json();
        
        document.getElementById('modalIp').textContent = data.ip;
        
        if (data.country_name || data.city) {
            document.getElementById('modalLocation').textContent = 
                [data.country_name, data.city].filter(Boolean).join(', ');
        } else {
            document.getElementById('modalLocation').textContent = 'Unknown';
        }
        
        document.getElementById('modalAsn').textContent = data.asn || 'N/A';
        document.getElementById('modalOrg').textContent = data.org || 'N/A';
        document.getElementById('modalPorts').textContent = data.total_ports || 0;
        document.getElementById('modalLastScan').textContent = formatTimestamp(data.last_scan);
        
        // Ports table
        if (data.ports && data.ports.length > 0) {
            document.getElementById('modalPortsTable').innerHTML = data.ports.map(port => `
                <tr class="border-b border-hacker-green/10">
                    <td class="py-2 text-hacker-green">${port.port}</td>
                    <td class="py-2 text-hacker-cyan">${port.protocol}</td>
                    <td class="py-2 text-hacker-purple">${port.service}</td>
                    <td class="py-2 text-gray-400 truncate max-w-xs">${port.banner || '-'}</td>
                </tr>
            `).join('');
        } else {
            document.getElementById('modalPortsTable').innerHTML = 
                '<tr><td colspan="4" class="text-center py-4 text-gray-500">No ports data</td></tr>';
        }
        
    } catch (error) {
        console.error('Host details error:', error);
        document.getElementById('modalLocation').textContent = 'Error loading';
    }
}

// Close Host Modal
function closeHostModal() {
    hostModal.classList.add('hidden');
    hostModal.classList.remove('flex');
}

// Load Stats
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats?limit=10`);
        
        if (!response.ok) throw new Error('Stats failed');
        
        const data = await response.json();
        
        document.getElementById('statHosts').textContent = formatNumber(data.total_hosts);
        document.getElementById('statRecords').textContent = formatNumber(data.total_records);
        document.getElementById('statServices').textContent = data.top_services.length;
        document.getElementById('statCountries').textContent = data.top_countries.length;
        document.getElementById('statPorts').textContent = data.top_ports.length;
        
        // Top services
        const topServicesEl = document.getElementById('topServices');
        if (data.top_services && data.top_services.length > 0) {
            const maxCount = data.top_services[0].count;
            topServicesEl.innerHTML = data.top_services.map(s => {
                const percentage = (s.count / maxCount) * 100;
                return `
                    <div class="flex items-center gap-3">
                        <span class="text-hacker-purple w-20 truncate text-xs">${s.service}</span>
                        <div class="flex-1 h-2 bg-hacker-darker rounded overflow-hidden">
                            <div class="h-full bg-hacker-purple" style="width: ${percentage}%"></div>
                        </div>
                        <span class="text-xs text-gray-500 w-12 text-right">${s.count}</span>
                    </div>
                `;
            }).join('');
        }
        
    } catch (error) {
        console.error('Stats error:', error);
    }
}

// Utility Functions
function getServiceClass(service) {
    if (!service) return 'service-default';
    const s = service.toLowerCase();
    if (s === 'ssh' || s === '22') return 'service-ssh';
    if (s === 'http' || s === '80') return 'service-http';
    if (s === 'https' || s === '443') return 'service-https';
    if (s === 'ftp' || s === '21') return 'service-ftp';
    return 'service-default';
}

function getCountryFlag(countryCode) {
    if (!countryCode) return '';
    const codePoints = [...countryCode.toUpperCase()]
        .map(c => 127397 + c.charCodeAt(0));
    return String.fromCodePoint(...codePoints);
}

function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    try {
        const date = new Date(timestamp);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return '-';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateTime() {
    const now = new Date();
    document.getElementById('currentTime').textContent = now.toISOString().slice(0, 19).replace('T', ' ');
}

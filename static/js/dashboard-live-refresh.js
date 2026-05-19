/**
 * Dashboard Live Refresh System
 * 
 * Automatically refreshes dashboard KPIs and transaction data every 10 seconds
 * Uses the /dashboard/api/live-stats/ endpoint to fetch live data
 */

(function() {
    'use strict';
    
    const DashboardLiveRefresh = {
        // Configuration
        config: {
            apiUrl: '/dashboard/api/live-stats/',
            refreshInterval: 10000, // 10 seconds
            maxRetries: 3,
            retryDelay: 2000, // 2 seconds
        },
        
        // State tracking
        state: {
            isRunning: false,
            retryCount: 0,
            lastSignature: null,
            timerId: null,
        },
        
        /**
         * Initialize the live refresh system
         */
        init: function() {
            console.log('[Dashboard] Initializing live refresh system...');
            
            if (this.state.isRunning) {
                console.warn('[Dashboard] Live refresh already running');
                return;
            }
            
            this.state.isRunning = true;
            this.state.retryCount = 0;
            
            // Initial refresh
            this.refresh();
            
            // Schedule recurring refreshes
            this.state.timerId = setInterval(() => this.refresh(), this.config.refreshInterval);
            
            console.log('[Dashboard] ✓ Live refresh initialized (interval: ' + this.config.refreshInterval + 'ms)');
        },
        
        /**
         * Stop the live refresh system
         */
        stop: function() {
            if (this.state.timerId) {
                clearInterval(this.state.timerId);
                this.state.timerId = null;
            }
            this.state.isRunning = false;
            console.log('[Dashboard] Live refresh stopped');
        },
        
        /**
         * Fetch live stats from the API
         */
        refresh: function() {
            const self = this;
            
            // Show loading indicator
            this.showLoadingIndicator();
            
            fetch(this.config.apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    self.state.retryCount = 0;  // Reset retry count on success
                    
                    // Check if data has changed
                    if (data.signature !== self.state.lastSignature) {
                        console.log('[Dashboard] ✓ Data updated at ' + new Date().toLocaleTimeString());
                        self.state.lastSignature = data.signature;
                        self.updateDashboard(data);
                        self.showNotification('Dashboard updated', 'success', 3000);
                    } else {
                        console.log('[Dashboard] No changes detected');
                    }
                } else {
                    throw new Error(data.message || 'Unknown error from API');
                }
            })
            .catch(error => {
                console.error('[Dashboard] Error fetching live stats:', error);
                self.handleError(error);
            })
            .finally(() => {
                self.hideLoadingIndicator();
            });
        },
        
        /**
         * Update dashboard elements with new data
         */
        updateDashboard: function(data) {
            const kpis = data.kpis;
            
            // Update KPI cards
            this.updateElement('today-revenue', kpis.today_revenue.toFixed(2), 'GHS ' + kpis.today_revenue.toFixed(2));
            this.updateElement('today-transactions', kpis.transaction_count, kpis.transaction_count + ' transactions');
            this.updateElement('today-fuel-dispensed', kpis.total_fuel_dispensed.toFixed(2), kpis.total_fuel_dispensed.toFixed(2) + ' L');
            this.updateElement('pending-payments', kpis.pending_payments, kpis.pending_payments + ' pending');
            this.updateElement('low-stock-count', kpis.low_stock_count, kpis.low_stock_count + ' low');
            this.updateElement('active-pumps', kpis.active_pumps + '/' + kpis.total_pumps, kpis.active_pumps + ' active pumps');
            
            // Update recent transactions table
            this.updateRecentTransactions(data.recent_transactions);
            
            // Trigger custom event for other scripts to listen to
            const event = new CustomEvent('dashboardUpdated', { detail: data });
            document.dispatchEvent(event);
        },
        
        /**
         * Update a single dashboard element
         */
        updateElement: function(elementId, value, displayText) {
            const element = document.getElementById(elementId);
            if (element) {
                const newText = displayText || value;
                if (element.textContent !== newText) {
                    element.textContent = newText;
                    element.classList.add('updated');
                    setTimeout(() => element.classList.remove('updated'), 1000);
                }
            }
        },
        
        /**
         * Update recent transactions table
         */
        updateRecentTransactions: function(transactions) {
            const tableBody = document.querySelector('table tbody');
            if (!tableBody) return;
            
            // Only update if we have transactions
            if (!transactions || transactions.length === 0) return;
            
            // Build new rows
            let newHtml = '';
            transactions.forEach(txn => {
                newHtml += `
                    <tr>
                        <td>${txn.transaction_id}</td>
                        <td>${txn.customer_name}</td>
                        <td>${txn.fuel_type}</td>
                        <td>GHS ${txn.amount.toFixed(2)}</td>
                        <td><span class="badge badge-success">${txn.status}</span></td>
                        <td>${txn.time}</td>
                    </tr>
                `;
            });
            
            tableBody.innerHTML = newHtml;
        },
        
        /**
         * Handle API errors with retry logic
         */
        handleError: function(error) {
            this.state.retryCount++;
            
            if (this.state.retryCount < this.config.maxRetries) {
                console.warn(`[Dashboard] Retrying... (${this.state.retryCount}/${this.config.maxRetries})`);
                this.showNotification('Connection lost, retrying...', 'warning', 2000);
                
                // Retry after delay
                setTimeout(() => this.refresh(), this.config.retryDelay);
            } else {
                console.error('[Dashboard] Max retries exceeded');
                this.showNotification('Failed to update dashboard', 'error', 5000);
            }
        },
        
        /**
         * Show loading indicator
         */
        showLoadingIndicator: function() {
            const indicator = document.getElementById('dashboard-loading');
            if (indicator) {
                indicator.style.display = 'block';
            }
        },
        
        /**
         * Hide loading indicator
         */
        hideLoadingIndicator: function() {
            const indicator = document.getElementById('dashboard-loading');
            if (indicator) {
                indicator.style.display = 'none';
            }
        },
        
        /**
         * Show notification toast
         */
        showNotification: function(message, type, duration) {
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#f59e0b'};
                color: white;
                border-radius: 4px;
                z-index: 9999;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                animation: slideIn 0.3s ease-out;
            `;
            
            document.body.appendChild(notification);
            
            if (duration > 0) {
                setTimeout(() => {
                    notification.style.animation = 'slideOut 0.3s ease-out';
                    setTimeout(() => notification.remove(), 300);
                }, duration);
            }
        },
    };
    
    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            DashboardLiveRefresh.init();
        });
    } else {
        DashboardLiveRefresh.init();
    }
    
    // Export for manual control
    window.DashboardLiveRefresh = DashboardLiveRefresh;
})();

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    .updated {
        animation: pulse 0.5s ease-out;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
`;
document.head.appendChild(style);

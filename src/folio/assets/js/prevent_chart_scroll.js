/**
 * Prevent chart scroll interference with page scrolling
 * 
 * This script prevents the charts from capturing wheel events when users
 * are trying to scroll through the page. It adds event listeners to all
 * chart elements to stop wheel events from propagating.
 */

// Wait for the document to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Function to prevent wheel events on charts
    function preventChartScroll() {
        // Find all chart containers
        const chartElements = document.querySelectorAll('.dash-chart');
        
        // Add event listeners to each chart
        chartElements.forEach(function(chart) {
            chart.addEventListener('wheel', function(e) {
                // Prevent the wheel event from being captured by the chart
                e.stopPropagation();
            }, true);
        });
        
        console.log('Chart scroll prevention initialized');
    }
    
    // Initialize on page load
    preventChartScroll();
    
    // Also run when the page content changes (for dynamically loaded charts)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                preventChartScroll();
            }
        });
    });
    
    // Observe the entire document for changes
    observer.observe(document.body, { 
        childList: true,
        subtree: true
    });
});

class ThemeManager {
    constructor() {
        this.theme = this.getStoredTheme() || this.getPreferredTheme();
        this.initializeTheme();
        this.attachEventListeners();
    }

    getStoredTheme() {
        return localStorage.getItem('theme');
    }

    getPreferredTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    setStoredTheme(theme) {
        localStorage.setItem('theme', theme);
    }

    setTheme(theme) {
        this.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        this.setStoredTheme(theme);
        this.updateToggleIcon();
        this.dispatchThemeChangeEvent();
    }

    toggleTheme() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    updateToggleIcon() {
        const toggleIcon = document.querySelector('.theme-toggle-icon');
        
        if (toggleIcon) {
            if (this.theme === 'dark') {
                toggleIcon.textContent = 'light_mode';
            } else {
                toggleIcon.textContent = 'dark_mode';
            }
        }
    }

    initializeTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
        this.updateToggleIcon();
    }

    attachEventListeners() {
        // Listen for theme toggle clicks
        document.addEventListener('click', (event) => {
            if (event.target.closest('.theme-toggle')) {
                event.preventDefault();
                this.toggleTheme();
            }
        });

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!this.getStoredTheme()) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Initialize toggle on DOM ready
        document.addEventListener('DOMContentLoaded', () => {
            this.updateToggleIcon();
        });
    }

    dispatchThemeChangeEvent() {
        const event = new CustomEvent('themeChange', {
            detail: { theme: this.theme }
        });
        window.dispatchEvent(event);
    }
}

// Initialize theme manager
const themeManager = new ThemeManager();

// Export for use in other scripts if needed
window.themeManager = themeManager;

// Auto-adjust charts and other dynamic content when theme changes
window.addEventListener('themeChange', (event) => {
    // Update any charts or dynamic content that needs theme-specific colors
    if (typeof Chart !== 'undefined') {
        Chart.helpers.each(Chart.instances, function(chart) {
            if (chart.options.plugins && chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = 
                    event.detail.theme === 'dark' ? '#e5e5e5' : '#212529';
            }
            if (chart.options.scales) {
                Object.keys(chart.options.scales).forEach(scaleKey => {
                    const scale = chart.options.scales[scaleKey];
                    if (scale.ticks) {
                        scale.ticks.color = event.detail.theme === 'dark' ? '#b0b0b0' : '#6c757d';
                    }
                    if (scale.grid) {
                        scale.grid.color = event.detail.theme === 'dark' ? '#404040' : '#dee2e6';
                    }
                });
            }
            chart.update();
        });
    }

    // Update any other theme-sensitive components
    console.log(`Theme changed to: ${event.detail.theme}`);
});
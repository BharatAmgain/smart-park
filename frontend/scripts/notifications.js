// Notification System for Smart Parking System

class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.createContainer();
    }

    createContainer() {
        if (!document.querySelector('.notification-container')) {
            const container = document.createElement('div');
            container.className = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(container);
            this.container = container;
        } else {
            this.container = document.querySelector('.notification-container');
        }
    }

    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');

        const colors = {
            success: { bg: '#d5f4e6', border: '#2ecc71', icon: '#2ecc71', text: '#27ae60' },
            error: { bg: '#f8d7da', border: '#e74c3c', icon: '#e74c3c', text: '#c0392b' },
            warning: { bg: '#fff3cd', border: '#f39c12', icon: '#f39c12', text: '#d68910' },
            info: { bg: '#d6eaf8', border: '#3498db', icon: '#3498db', text: '#2980b9' }
        };

        const color = colors[type] || colors.info;
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        notification.style.cssText = `
            background: ${color.bg};
            border-left: 4px solid ${color.border};
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideInRight 0.3s ease;
            min-width: 280px;
            max-width: 350px;
        `;

        notification.innerHTML = `
            <i class="fas ${icons[type]}" style="color: ${color.icon}; font-size: 20px;"></i>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: ${color.text}; margin-bottom: 4px;">
                    ${type.charAt(0).toUpperCase() + type.slice(1)}
                </div>
                <div style="color: #666; font-size: 14px;">${message}</div>
            </div>
            <button class="btn-close" style="font-size: 12px; padding: 0;"></button>
        `;

        const closeBtn = notification.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => this.remove(notification));

        this.container.appendChild(notification);

        // Auto remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                this.remove(notification);
            }
        }, duration);

        this.notifications.push(notification);
        return notification;
    }

    remove(notification) {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
        this.notifications = this.notifications.filter(n => n !== notification);
    }

    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 5000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 5000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }

    clearAll() {
        this.notifications.forEach(n => this.remove(n));
    }
}

// Global notification manager
const notifications = new NotificationManager();

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
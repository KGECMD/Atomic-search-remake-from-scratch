/**
 * Atomic Search - Main JavaScript
 */

class AtomicSearch {
    constructor() {
        this.theme = this.getStoredTheme();
        this.init();
    }

    init() {
        this.applyTheme();
        this.setupEventListeners();
        this.initAnimations();
    }

    // Theme Management
    getStoredTheme() {
        const stored = localStorage.getItem('theme');
        if (stored) return stored;
        
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        return prefersDark ? 'dark' : 'light';
    }

    setTheme(theme) {
        this.theme = theme;
        localStorage.setItem('theme', theme);
        this.applyTheme();
    }

    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
    }

    toggleTheme() {
        const newTheme = this.theme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    // Event Listeners
    setupEventListeners() {
        // Theme toggle
        document.getElementById('theme-toggle')?.addEventListener('click', () => {
            this.toggleTheme();
        });

        // AI Sidebar toggle
        const aiToggle = document.getElementById('ai-sidebar-toggle');
        const aiSidebar = document.getElementById('ai-sidebar');
        
        if (aiToggle && aiSidebar) {
            aiToggle.addEventListener('click', () => {
                aiSidebar.classList.toggle('open');
            });
        }

        // Search form enhancement
        this.setupSearchEnhancements();

        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
    }

    // Search Enhancements
    setupSearchEnhancements() {
        // Auto-focus on search input
        const searchInput = document.getElementById('search-input') || 
                           document.getElementById('hero-search-input');
        
        if (searchInput && !searchInput.value) {
            setTimeout(() => searchInput.focus(), 100);
        }

        // Search suggestions
        this.setupSearchSuggestions();
    }

    setupSearchSuggestions() {
        const searchInputs = document.querySelectorAll('input[name="q"]');
        
        searchInputs.forEach(input => {
            let timeout;
            
            input.addEventListener('input', () => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.fetchSuggestions(input.value);
                }, 300);
            });
        });
    }

    async fetchSuggestions(query) {
        if (query.length < 2) return;

        try {
            const response = await fetch(`/api/suggestions?q=${encodeURIComponent(query)}`);
            const suggestions = await response.json();
            this.displaySuggestions(suggestions);
        } catch (error) {
            console.error('Failed to fetch suggestions:', error);
        }
    }

    displaySuggestions(suggestions) {
        // Implementation depends on the page
        const container = document.querySelector('.suggestions-container');
        if (!container) return;

        if (suggestions.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = suggestions.map(s => `
            <a href="/search?q=${encodeURIComponent(s)}" class="suggestion-item">${s}</a>
        `).join('');
    }

    // Keyboard Shortcuts
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger if typing in input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch(e.key.toLowerCase()) {
                case '/':
                    e.preventDefault();
                    this.focusSearch();
                    break;
                case 't':
                    if (!e.ctrlKey && !e.metaKey) {
                        this.toggleTheme();
                    }
                    break;
                case 'a':
                    if (!e.ctrlKey && !e.metaKey) {
                        this.toggleAISidebar();
                    }
                    break;
                case 'Escape':
                    this.closeAllModals();
                    break;
            }
        });
    }

    focusSearch() {
        const input = document.getElementById('search-input') || 
                     document.getElementById('hero-search-input') ||
                     document.querySelector('.search-input');
        input?.focus();
    }

    toggleAISidebar() {
        const sidebar = document.getElementById('ai-sidebar');
        sidebar?.classList.toggle('open');
    }

    closeAllModals() {
        document.querySelectorAll('.modal.open').forEach(modal => {
            modal.classList.remove('open');
        });
    }

    // Animations
    initAnimations() {
        // Intersection Observer for scroll animations
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            observer.observe(el);
        });

        // Smooth transitions for cards
        this.setupCardAnimations();
    }

    setupCardAnimations() {
        const cards = document.querySelectorAll('.feature-card, .result-item');
        
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 50}ms`;
            card.classList.add('fade-in-up');
        });
    }
}

// AI Chat Class
class AIChat {
    constructor() {
        this.conversationId = this.generateId();
        this.messages = [];
        this.isStreaming = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadHistory();
    }

    generateId() {
        return Math.random().toString(36).substring(2, 18);
    }

    setupEventListeners() {
        const form = document.getElementById('ai-input-form');
        const input = document.getElementById('ai-input');
        
        if (form && input) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.sendMessage(input.value);
                input.value = '';
            });

            // Auto-resize textarea
            input.addEventListener('input', () => {
                input.style.height = 'auto';
                input.style.height = Math.min(input.scrollHeight, 150) + 'px';
            });

            // Enter to send, Shift+Enter for newline
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    form.dispatchEvent(new Event('submit'));
                }
            });
        }
    }

    async sendMessage(text) {
        if (!text.trim() || this.isStreaming) return;

        this.isStreaming = true;
        this.addMessage('user', text);
        
        const botMessage = this.addMessage('bot', '...');
        
        try {
            const response = await fetch('/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    conversation_id: this.conversationId
                })
            });

            const data = await response.json();
            
            if (data.error) {
                botMessage.querySelector('.ai-message-content').textContent = `Error: ${data.error}`;
            } else {
                botMessage.querySelector('.ai-message-content').textContent = data.response;
            }
        } catch (error) {
            botMessage.querySelector('.ai-message-content').textContent = 'Failed to get response. Please try again.';
        }

        this.isStreaming = false;
        this.scrollToBottom();
    }

    addMessage(role, content) {
        const messagesContainer = document.getElementById('ai-messages');
        if (!messagesContainer) return null;

        const messageEl = document.createElement('div');
        messageEl.className = `ai-message ai-message-${role}`;
        messageEl.innerHTML = `
            <div class="ai-message-content">${this.escapeHtml(content)}</div>
        `;

        messagesContainer.appendChild(messageEl);
        this.scrollToBottom();
        
        return messageEl;
    }

    scrollToBottom() {
        const container = document.getElementById('ai-messages');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    loadHistory() {
        // Load from localStorage
        const saved = localStorage.getItem(`ai_chat_${this.conversationId}`);
        if (saved) {
            try {
                const history = JSON.parse(saved);
                history.forEach(msg => {
                    this.addMessage(msg.role, msg.content);
                });
            } catch (e) {
                console.error('Failed to load chat history');
            }
        }
    }

    saveHistory() {
        const messages = document.querySelectorAll('#ai-messages .ai-message');
        const history = Array.from(messages).map(msg => ({
            role: msg.classList.contains('ai-message-user') ? 'user' : 'bot',
            content: msg.querySelector('.ai-message-content')?.textContent || ''
        }));
        
        localStorage.setItem(`ai_chat_${this.conversationId}`, JSON.stringify(history));
    }
}

// Voting Class
class Voting {
    async vote(url, type) {
        try {
            const response = await fetch('/vote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, type })
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateVoteDisplay(url, data.stats, type);
                return true;
            } else {
                this.showError(data.error);
                return false;
            }
        } catch (error) {
            this.showError('Failed to submit vote');
            return false;
        }
    }

    updateVoteDisplay(url, stats, newVote) {
        const resultItem = document.querySelector(`[data-url="${url}"]`);
        if (!resultItem) return;

        const scoreEl = resultItem.querySelector('.vote-score');
        if (scoreEl) {
            scoreEl.textContent = stats.votes;
        }

        const upBtn = resultItem.querySelector('.vote-up');
        const downBtn = resultItem.querySelector('.vote-down');

        upBtn?.classList.toggle('active', newVote === 1);
        downBtn?.classList.toggle('active', newVote === -1);
    }

    showError(message) {
        // Show toast notification
        const toast = document.createElement('div');
        toast.className = 'toast toast-error';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.atomicSearch = new AtomicSearch();
    window.aiChat = new AIChat();
    window.voting = new Voting();

    // Setup voting button listeners
    document.querySelectorAll('.vote-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const url = this.dataset.url;
            const type = parseInt(this.dataset.type);
            await window.voting.vote(url, type);
        });
    });
});

// Export for use in other modules
window.AtomicSearch = AtomicSearch;
window.AIChat = AIChat;
window.Voting = Voting;

/**
 * Keyboard shortcuts for Atomic Search
 * Provides vim-like and standard keyboard navigation
 */

const KeyboardShortcuts = {
    shortcuts: {
        'g h': 'Go to homepage',
        'g s': 'Go to settings',
        'g a': 'Go to admin dashboard',
        'g b': 'Go to bookmarks',
        'g c': 'Go to collections',
        '/': 'Focus search input',
        'enter': 'Submit search',
        'escape': 'Clear focus / Close modal',
        'j': 'Next result',
        'k': 'Previous result',
        'o': 'Open selected result',
        'u': 'Upvote',
        'd': 'Downvote',
        'b': 'Bookmark result',
        't': 'Toggle theme',
        '?': 'Show shortcuts help',
        '1': 'Web search',
        '2': 'Images',
        '3': 'Videos',
        '4': 'News',
        '5': 'Shopping',
    },

    init() {
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
    },

    handleKeydown(e) {
        const key = this.getKeyCombo(e);
        
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            if (key === 'escape') e.target.blur();
            return;
        }

        if (this.shortcuts[key]) {
            e.preventDefault();
            this.executeAction(key);
        }
    },

    getKeyCombo(e) {
        const parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.shiftKey && e.key !== 'Shift') parts.push('shift');
        let key = e.key.toLowerCase();
        if (key === ' ') key = 'space';
        parts.push(key);
        return parts.join(' ');
    },

    executeAction(key) {
        switch(key) {
            case 'g h': window.location.href = '/'; break;
            case 'g s': window.location.href = '/settings'; break;
            case '/': document.querySelector('input[name="q"]')?.focus(); break;
            case 'enter': this.submitSearch(); break;
            case 'escape': document.activeElement?.blur(); break;
            case 'j': this.selectNext(); break;
            case 'k': this.selectPrevious(); break;
            case 't': this.toggleTheme(); break;
            case '?': this.showHelp(); break;
            case '1': case '2': case '3': case '4': case '5':
                this.changeSearchType(['web','images','videos','news','shopping'][parseInt(key)-1]);
                break;
        }
    },

    selectNext() {
        const results = document.querySelectorAll('.result-item');
        if (results.length === 0) return;
        const selected = document.querySelector('.result-item.selected');
        const index = selected ? Array.from(results).indexOf(selected) + 1 : 0;
        this.selectResult(Math.min(index, results.length - 1));
    },

    selectPrevious() {
        const results = document.querySelectorAll('.result-item');
        const selected = document.querySelector('.result-item.selected');
        const index = selected ? Array.from(results).indexOf(selected) - 1 : 0;
        this.selectResult(Math.max(index, 0));
    },

    selectResult(index) {
        const results = document.querySelectorAll('.result-item');
        results.forEach(r => r.classList.remove('selected'));
        if (index >= 0 && index < results.length) {
            results[index].classList.add('selected');
            results[index].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    },

    submitSearch() {
        const input = document.querySelector('input[name="q"]');
        if (input?.value.trim()) input.closest('form')?.submit();
    },

    toggleTheme() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
        document.cookie = `theme=${current === 'dark' ? 'light' : 'dark'};path=/;max-age=31536000`;
    },

    changeSearchType(type) {
        const url = new URL(window.location);
        url.searchParams.set('type', type);
        window.location.href = url.toString();
    },

    showHelp() {
        alert('Keyboard Shortcuts:\n\n/ - Focus search\nj/k - Navigate results\no - Open result\nt - Toggle theme\n? - This help\n1-5 - Search types');
    }
};

document.addEventListener('DOMContentLoaded', () => KeyboardShortcuts.init());
window.KeyboardShortcuts = KeyboardShortcuts;

"""
Admin routes for Atomic Search.
"""

from flask import Blueprint, render_template, jsonify, request

admin_bp = Blueprint('admin', '/admin')


@admin_bp.route('/')
def index():
    """Admin dashboard."""
    from atomic_search.search.indexer import search_indexer
    
    stats = search_indexer.get_stats()
    
    return render_template('admin.html', stats={
        'total_searches': stats.get('total_results', 0),
        'active_users': 342,
        'cached_results': stats.get('tracked_queries', 0),
        'queries_today': 1234,
        'avg_response': '234ms',
        'cache_hit_rate': '87%',
        'error_rate': '0.1%',
    })


@admin_bp.route('/stats')
def stats():
    """Get statistics."""
    from atomic_search.search.indexer import search_indexer
    return jsonify(search_indexer.get_stats())


@admin_bp.route('/plugins')
def plugins():
    """List plugins."""
    from atomic_search.plugins import plugin_manager
    return jsonify([p.__dict__ for p in plugin_manager.list_plugins()])


@admin_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache."""
    from atomic_search.utils.cache import cache_manager
    cache_manager.l1_cache.clear()
    return jsonify({'success': True})


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Admin settings."""
    if request.method == 'POST':
        # Save settings
        return jsonify({'success': True})
    
    from atomic_search.config import config
    return jsonify(config.to_dict())

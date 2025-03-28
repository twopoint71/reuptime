from flask import send_from_directory, render_template

def register_static_routes(app):
    """Register routes for serving static files."""

    @app.route('/')
    def home():
	    return render_template('summary.html')

    @app.route('/favicon.ico')
    def favicon():
        """Serve the favicon.ico file."""
        return send_from_directory('static', 'favicon.ico')

    @app.route('/admin')
    def admin():
	    return render_template('admin.html')

    @app.route('/unmonitored_hosts')
    def unmonitored_hosts():
	    return render_template('unmonitored_hosts.html')

    @app.route('/monitored_hosts')
    def monitored_hosts():
	    return render_template('monitored_hosts.html')

    @app.route('/monitor_log')
    def monitor_log():
	    return render_template('monitor_log.html')

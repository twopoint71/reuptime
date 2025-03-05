from flask import send_from_directory

def register_static_routes(app):
    """Register routes for serving static files."""
    
    @app.route('/')
    def index():
        """Serve the main index.html page."""
        return send_from_directory('static', 'index.html')
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve the favicon.ico file."""
        return send_from_directory('static', 'favicon.ico')

    @app.route('/deleted_hosts')
    def deleted_hosts():
        """Serve the deleted_hosts.html page."""
        return send_from_directory('static', 'deleted_hosts.html')
    
    @app.route('/host/<int:host_id>')
    def host_details(host_id):
        """Redirect to the main page with a query parameter to open the host details modal."""
        return send_from_directory('static', 'index.html') 
from app import start_app

# Create app instance from factory module
app = start_app()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
from apps import app

# Flask起動
app = app.create_app()

if __name__ == "__main__":
    app.run(debug=True)
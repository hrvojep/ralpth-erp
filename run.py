#!/usr/bin/env python3
from erp.app import create_app

app = create_app()

if __name__ == "__main__":
    print("ERP System running at http://0.0.0.0:8080")
    print("Login: admin / admin")
    app.run(debug=True, host="0.0.0.0", port=8080)

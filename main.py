#!/usr/bin/env python3
from memorizer.application import create_app
import sys

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'db' and sys.argv[2] == 'upgrade':
        app = create_app()
        with app.app_context():
            # Здесь выполняйте миграцию базы данных
            from memorizer.database import db
            from flask_migrate import upgrade
            upgrade(directory="migrations")
    else:
        app = create_app()
        app.run(debug=True)
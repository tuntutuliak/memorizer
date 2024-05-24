from click import Command, argument

from memorizer import models
from memorizer.database import db


class AdminCommand(Command):
    """Make user administrator"""

    def __init__(self):
        super().__init__(name='admin')

    @argument('username', type=str)
    def run(self, username):
        user = models.User.query.filter_by(username=username).first()
        if not user:
            print(f"Did not find a user with username {username}")
            return
        user.admin = True
        db.session.add(user)
        db.session.commit()
        print(f"{username} is now an administrator")

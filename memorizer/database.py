from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_continuum import make_versioned
from sqlalchemy_continuum.plugins import FlaskPlugin
from sqlalchemy_utils import force_auto_coercion

from memorizer.user import get_user

db = SQLAlchemy()

force_auto_coercion()


# Функция для получения идентификатора текущего пользователя
def fetch_current_user_id():
    user = get_user()
    # Возвращаем идентификатор текущего пользователя
    return getattr(user, 'id', None)


make_versioned(plugins=[FlaskPlugin(current_user_id_factory=fetch_current_user_id)])

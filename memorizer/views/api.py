import json

from flask import Blueprint, Response, request
from flask.views import MethodView

from memorizer import forms, models, utils
from memorizer.cache import cache
from memorizer.config import CACHE_TIME
from memorizer.user import get_user

api = Blueprint('api', __name__)


def error(message):
    return {'message': message}


class CacheView(object):
    def __repr__(self):
        """Hack to make memoization work with self and different get parameters"""
        return '%s (%s)' % (self.__class__.__name__, request.args)


class JsonView(MethodView):
    def dispatch_request(self, *args, **kwargs):
        """Returns a json document with mimetype set"""
        return Response(
            json.dumps(super(JsonView, self).dispatch_request(*args, **kwargs)),
            mimetype='application/json'
        )


# REST API

class APIView(JsonView, CacheView):
    model = None
    form = None

    @cache.memoize(CACHE_TIME)
    def get(self, object_id=None):
        # Get a single object
        if object_id:
            object = self.model.query.get_or_404(object_id)
            return object.serialize()
        # Get all
        else:
            filters = {}
            # Filtering with query string parameters
            query = self.model.query
            for key in request.args.keys():
                model_columns = self.model.__table__.columns.keys()
                if key in model_columns:
                    value = request.args.getlist(key)
                    # SQL IN
                    if len(value) > 1:
                        # Not super pretty, but it works™
                        attr = getattr(self.model, key)
                        query = query.filter(attr.in_(value))
                    # SQL AND
                    else:
                        filters[key] = value[0]
            objects = query.filter_by(**filters)
            serialized_objects = [object.serialize() for object in objects]
            return [obj for obj in serialized_objects if obj is not None]

    def post(self):
        response = {}
        user = get_user()
        if not user.registered:
            response['errors'] = [error('Not logged in')]
            return response
        form = self.form(request.form)
        response['success'] = form.validate()
        if form.validate():
            # Inserting
            object = self.model()
            form.populate_obj(object)
            models.db.session.add(object)
            models.db.session.commit()
            # Deleting cache
            cache.clear()
        else:
            response['errors'] = form.errors
        return response

    def put(self, object_id):
        response = {'success': False}
        user = get_user()
        if not user.registered:
            response['errors'] = [error('Not logged in')]
            return response
        object = self.model.query.get(object_id)
        if not object:
            response['errors'] = [error('Item not found')]
            return response
        form = self.form(request.form, obj=object)
        form.populate_obj(object)
        response['success'] = form.validate()
        if response['success']:
            models.db.session.add(object)
            models.db.session.commit()
            # Deleting cache
            cache.clear()
        else:
            response['errors'] = form.errors
        return response

    def delete(self, object_id):
        response = {}
        user = get_user()
        if not user.admin:
            response['errors'] = [error('Admin access required')]
            return response
        object = self.model.query.get(object_id)
        if object:
            models.db.session.delete(object)
            models.db.session.commit()
            # Deleting cache
            cache.clear()
        return {'success': bool(object)}


class CourseAPI(APIView):
    model = models.Course
    form = forms.CourseForm


class ExamAPI(APIView):
    model = models.Exam
    form = forms.ExamForm


class QuestionAPI(APIView):
    model = models.Question
    form = forms.QuestionForm


class AlternativeAPI(APIView):
    model = models.Alternative
    form = forms.AlternativeForm


def register_api(view, endpoint, url, pk='object_id', pk_type='int'):
    view_func = view.as_view(endpoint)
    api.add_url_rule(url, defaults={pk: None},
                     view_func=view_func, methods=['GET'])
    api.add_url_rule(url, view_func=view_func, methods=['POST'])
    api.add_url_rule('%s<%s:%s>' % (url, pk_type, pk), view_func=view_func,
                     methods=['GET', 'PUT', 'DELETE'])


register_api(CourseAPI, 'course_api', '/courses/')
register_api(ExamAPI, 'exam_api', '/exams/')
register_api(QuestionAPI, 'question_api', '/questions/')
register_api(AlternativeAPI, 'alterative_api', '/alternatives/')


# Helper apis

class CourseQuestions(JsonView, CacheView):
    @cache.memoize(CACHE_TIME)
    def get(self, course):
        course_m = models.Course.query.filter_by(code=course).first_or_404()
        questions = models.Question.query.filter_by(course=course_m).all()
        serialized_objects = [question_m.serialize() for question_m in questions]
        return [obj for obj in serialized_objects if obj is not None]


class ExamQuestions(JsonView, CacheView):
    @cache.memoize(CACHE_TIME)
    def get(self, course, exam):
        course_m = models.Course.query.filter_by(code=course).first_or_404()
        exam_m = models.Exam.query.filter_by(course=course_m, name=exam).first_or_404()
        serialized_objects = [question_m.serialize() for question_m in exam_m.questions]
        return [obj for obj in serialized_objects if obj is not None]


api.add_url_rule('/questions/<string:course>/all/', view_func=CourseQuestions.as_view('course_questions'))
api.add_url_rule('/questions/<string:course>/<string:exam>/', view_func=ExamQuestions.as_view('exam_questions'))


class Stats(JsonView):
    def get(self, course_code, exam_name=None):
        return utils.generate_stats(course_code, exam_name)


api.add_url_rule('/stats/<string:course_code>/<string:exam_name>/', view_func=Stats.as_view('stats_exam'))
api.add_url_rule('/stats/<string:course_code>/', view_func=Stats.as_view('stats_course'))


def correct_alternatives(question):
    alts = models.Alternative.query.filter_by(question=question, correct=True)
    return {alt.id for alt in alts}


class Answer(JsonView):
    def post(self):
        try:
            question_id = int(request.form.get('question'))
        except ValueError:
            return error('Missing question')
        question = models.Question.query.get_or_404(question_id)
        if question.multiple:
            try:
                answer_alt = set(map(int, request.form.getlist('alternative')))
            except ValueError:
                return error('Missing alternative')
            correct_alt = correct_alternatives(question)
            # Checking if all alternatives are correct
            if question.exam.multiple_correct:
                correct = correct_alt == answer_alt
            else:
                correct = correct_alt >= answer_alt
        else:
            # Yes/No
            answer = request.form.get('correct', False) == 'true'
            correct = question.correct == answer
        user = get_user()
        answered = models.Stats.answered(user, question)
        if not answered:
            stat = models.Stats(user, question, correct)
            models.db.session.add(stat)
            models.db.session.commit()
        return {'success': not answered, 'correct': correct}


api.add_url_rule('/answer', view_func=Answer.as_view('answer'), methods=['POST'])


class RandomQuestion(JsonView):
    def get(self, course_code, exam_name=None):
        current = request.args.get('id', -1)
        try:
            current = int(current)
        except ValueError:
            current = -1
        return {'index': utils.random_id(id=current, course=course_code, exam=exam_name)}


api.add_url_rule(
    '/random/<string:course_code>/<string:exam_name>/',
    view_func=RandomQuestion.as_view('random_question_exam')
)
api.add_url_rule(
    '/random/<string:course_code>/',
    view_func=RandomQuestion.as_view('random_question_course')
)

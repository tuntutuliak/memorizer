var API = function(url) {
    this.url = url || null;
};

API.prototype.send = function(filters, callback, method) {
    Ajax({url: this.url, data: filters, method: method || 'GET'}, {
        success: function(data) {
            callback(data);
        },
        error: function(data) {
            Alert('Не удалось получить данные. Попробуйте перезагрузить страницу.', 'error');
        }
    });
};

var CourseAPI = function() {
    API.call(this);
    this.url = '/api/courses/';
};

CourseAPI.prototype = Object.create(API.prototype);

CourseAPI.prototype.getByCode = function(code, callback) {
    this.send({code: code}, callback);
};

var ExamAPI = function() {
    API.call(this);
    this.url = '/api/exams/';
};

ExamAPI.prototype = Object.create(API.prototype);

ExamAPI.prototype.examIds = function(course_id, callback) {
    this.send({course_id: course_id}, function(exams) {
        var ids = [];
        for(var i = 0; i < exams.length; i++) {
            ids.push(exams[i].id);
        }
        callback(ids);
    }.bind(this));
};

var QuestionAPI = function() {
    API.call(this);
    this.url = '/api/questions/';
};

QuestionAPI.prototype = Object.create(API.prototype);

QuestionAPI.prototype.questions = function(exams, callback) {
    this.send({exam_id: exams}, callback);
};

var AnswerAPI = function() {
    API.call(this);
    this.url = '/api/answer';
};

AnswerAPI.prototype = Object.create(API.prototype);

AnswerAPI.prototype.submit = function(question_id, answer, callback) {
    var params = {};
    if(typeof answer === 'boolean') {
        params = {question: question_id, correct: answer};
    }
    // Alternatives (can be several)
    else if(['number', 'object'].indexOf(typeof answer) !== -1) {
        params = {question: question_id, alternative: answer};
    }
    this.send(params, callback, 'POST');
};

var StatsAPI = function(course, exam) {
    API.call(this);
    this.url = '/api/stats';
    if(course !== undefined) {
        this.url += '/' + course + '/';
    }
    if(exam !== undefined) {
        this.url += exam + '/';
    }
};

StatsAPI.prototype = Object.create(API.prototype);

StatsAPI.prototype.get = function(callback) {
    this.send(null, callback);
};

var RandomQuestionAPI = function(course, exam) {
    API.call(this);
    this.url = '/api/random';
    if(course !== undefined) {
        this.url += '/' + course + '/';
    }
    if(exam !== undefined) {
        this.url += exam + '/';
    }
};

RandomQuestionAPI.prototype = Object.create(API.prototype);

RandomQuestionAPI.prototype.get = function(id, callback) {
    this.send({ id: id }, callback);
};

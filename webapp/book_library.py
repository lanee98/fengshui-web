"""Local-only book catalogue; never copy private PDFs into public static assets."""
from pathlib import Path
from flask import jsonify, send_file, request

ROOT = Path('D:/AI＋创新/风水课/风水书籍')
SPECS = [
 ('origins','风水探源','历史源流与文化背景','风水探源'),
 ('housing','住宅设计解剖书','床位、窗户与生活动线','住宅设计解剖书'),
 ('theory','风水理论研究（第2版）','传统空间观念与环境心理','风水理论研究'),
 ('classic','图解阳宅十书','传统住宅形法与门、床、灶的文化背景','图解阳宅十书'),
 ('interior','室内设计资料集','家具尺度、室内设计与陈设资料','室内设计资料集'),
 ('standard','GB 55038—2025 住宅项目规范','现代住宅规范；与传统文化依据分开阅读','GB55038-2025'),
]

def install_book_library(app):
    def files():
        return {key: next(iter(ROOT.glob(prefix+'*.pdf')), None) for key, title, topic, prefix in SPECS}

    @app.get('/api/book-references')
    def catalogue():
        available = files()
        return jsonify(books=[{'id': key, 'title': title, 'topic': topic, 'available': bool(available[key]), 'status': '已收录本地文件；具体原文与页码待核对', 'url': '/api/book-references/'+key+'/pdf'} for key,title,topic,prefix in SPECS])

    @app.get('/api/book-references/<key>/pdf')
    def book_pdf(key):
        # Reading is explicitly local; deploying this code does not publish books.
        if request.remote_addr not in ('127.0.0.1', '::1'):
            return jsonify(error='书籍仅供本机阅读'), 403
        path = files().get(key)
        if not path:
            return jsonify(error='本机未找到该书籍'), 404
        return send_file(path, mimetype='application/pdf', conditional=True)

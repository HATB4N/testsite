from flask import Flask, request, render_template, redirect, url_for, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image
from googleapiclient.discovery import build
from pytz import timezone
from datetime import datetime
import os
import random

app = Flask(__name__)

YOUTUBE_API_KEY = ''
PLAYLIST_ID = ''
ADMIN_PASSWORD = ''

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

kst = timezone('Asia/Seoul')

# Database models
# Database models
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    text = db.Column(db.String(500))
    post_comments = db.relationship('PostComment', backref='post', lazy=True)
    time = db.Column(db.DateTime, default=datetime.now(kst))

    def __init__(self, ip, text):
        self.ip = ip
        self.text = text

class PostComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    text = db.Column(db.String(500))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now(kst))

    def __init__(self, ip, text, post_id):
        self.ip = ip
        self.text = text
        self.post_id = post_id

class NewsArticle(db.Model):
    __tablename__ = 'news_article'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_ip = db.Column(db.String(45), nullable=False)
    view_count = db.Column(db.Integer, default=0)
    article_comments = db.relationship('ArticleComment', backref='news_article', lazy=True)
    time = db.Column(db.DateTime, default=datetime.now(kst))

    def __init__(self, title, content, author_ip):
        self.title = title
        self.content = content
        self.author_ip = author_ip

    def __repr__(self):
        return f'<NewsArticle {self.title}>'

class ArticleComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    text = db.Column(db.String(500))
    article_id = db.Column(db.Integer, db.ForeignKey('news_article.id'), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now(kst))

    def __init__(self, ip, text, article_id):
        self.ip = ip
        self.text = text
        self.article_id = article_id


with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_youtube_videos(api_key, playlist_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=50  # 재생목록의 최대 비디오 수
    )
    response = request.execute()
    videos = response['items']
    video_ids = [video['snippet']['resourceId']['videoId'] for video in videos]
    return video_ids

def ip_blind(ip):
    return '.'.join(ip.split('.')[:2]) + '.x.x'

@app.route('/')
def index():
    user_ip = ip_blind(request.remote_addr)
    video_ids = get_youtube_videos(YOUTUBE_API_KEY, PLAYLIST_ID)
    random_videos = random.sample(video_ids, 3)
    recent_articles = NewsArticle.query.order_by(NewsArticle.time.desc()).limit(5).all()
    recent_posts = Post.query.order_by(Post.id.desc()).limit(5).all()

    return render_template('index.html', ip=user_ip, videos=random_videos, recent_articles=recent_articles, recent_posts=recent_posts)

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, request.path[1:])

@app.errorhandler(404)
def page_not_found(error):
    return "페이지를 찾을 수 없습니다.", 404

@app.errorhandler(400)
def bad_request(error):
    return "잘못된 요청입니다.", 400

@app.errorhandler(401)
def unauthorized(error):
    return "권한이 없습니다.", 401


# Cyber Toilet
@app.route('/ct')
def ct():
    user_ip = ip_blind(request.remote_addr)
    posts = Post.query.order_by(Post.id.desc()).all()
    post_comments = PostComment.query.all()  # 모든 댓글을 가져옵니다.
    return render_template('ct.html', ip=user_ip, posts=posts, post_comments=post_comments)


@app.route('/ct/post', methods=['POST'])
def post_message():
    message_text = request.form.get('message')
    user_ip = ip_blind(request.remote_addr)
    if message_text:
        if message_text.strip().lower() == '/delete all':
            delete_all_messages()
        else:
            new_post = Post(ip=user_ip, text=message_text)
            db.session.add(new_post)
            db.session.commit()
    return redirect(url_for('ct'))

@app.route('/ct/comment/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    comment_text = request.form.get('comment')
    user_ip = ip_blind(request.remote_addr)
    if comment_text:
        new_comment = PostComment(ip=user_ip, text=comment_text, post_id=post_id)
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for('ct'))

def delete_all_messages():
    db.session.query(Post).delete()
    db.session.query(PostComment).delete()
    db.session.commit()
    print("Deleted all posts and comments.")

# Techno Ssiang Nian
@app.route('/ts/')
def news_list():
    articles = NewsArticle.query.order_by(NewsArticle.id.desc()).all()
    return render_template('news_list.html', articles=articles)

@app.route('/ts/<int:article_id>')
def news_detail(article_id):
    article = NewsArticle.query.get_or_404(article_id)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{article_id}.png')
    if os.path.exists(image_path):
        article.image_path = f'/uploads/{article_id}.png'
    
    article.view_count += 1
    db.session.commit()

    # 해당 기사에 대한 댓글도 가져옵니다.
    comments = ArticleComment.query.filter_by(article_id=article_id).order_by(ArticleComment.id.desc()).all()

    return render_template('news_detail.html', article=article, comments=comments)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = secure_filename(file.filename)
        # Save the original image to the UPLOAD_FOLDER directory
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Convert the image to PNG format if it's not already in PNG format
        image = Image.open(file_path)
        if image.format != 'PNG':
            # Change the file extension to '.png' and save the image
            new_filename = os.path.splitext(filename)[0] + '.png'
            new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            image.save(new_file_path)
            os.remove(file_path)  # Remove the original file
            
            # Update the filename to the new PNG filename
            filename = new_filename

        return 'File uploaded successfully'

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/ts/write', methods=['GET', 'POST'])
def write_news():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        user_ip = ip_blind(request.remote_addr)
        article = NewsArticle(title=title, content=content, author_ip=user_ip)
        db.session.add(article)
        db.session.commit()

        # Check if an image file is uploaded and allowed
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                # Save the image to the UPLOAD_FOLDER directory with the article ID as filename
                image_id = article.id
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], f'{image_id}.png'))

        return redirect(url_for('news_list'))
    
    return render_template('write_news.html')

@app.route('/ts/comment/<int:article_id>', methods=['POST'])
def ts_comment_post(article_id):
    comment_text = request.form.get('comment')
    user_ip = ip_blind(request.remote_addr)
    if comment_text:
        new_comment = ArticleComment(ip=user_ip, text=comment_text, article_id=article_id)
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for('news_detail', article_id=article_id))

@app.route('/admin')
def admin_dashboard():
    return render_template('admin.html')

@app.route('/admin/delete_article', methods=['POST'])
def delete_article():
    # 사용자가 입력한 비밀번호 확인
    password = request.form.get('password')
    if password != ADMIN_PASSWORD:
        abort(401)  # 401 Unauthorized 에러 반환
    
    article_id = request.form.get('article_id')
    if article_id:
        # 기사 삭제
        article = NewsArticle.query.get(article_id)
        if article:
            # 관련 이미지 파일도 삭제
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{article_id}.png')
            if os.path.exists(image_path):
                os.remove(image_path)
            
            db.session.delete(article)
            db.session.commit()
            return f"게시글 ID {article_id} 삭제됨"
        else:
            abort(404)  # 404 Not Found 에러 반환
    else:
        # 게시글 ID가 제공되지 않은 경우
        abort(400)  # 400 Bad Request 에러 반환

if __name__ == '__main__':
    app.run()
